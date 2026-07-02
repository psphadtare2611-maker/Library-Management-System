# ============================================================================
# ui/circulation_view.py
# ----------------------------------------------------------------------------
# ISSUE BOOK SCREEN — lend an available book to a borrower.
#
# Workflow:
#   - Select a Book (dropdown lists only AVAILABLE books)
#   - Select a Borrower (dropdown lists active borrowers)
#   - Issue Date            (defaults to today)
#   - Expected Return Date  (defaults to today + LOAN_PERIOD_DAYS)
#   - Press Issue -> CirculationService.issue_book() does all the verification
#     (book/borrower exist, book is Available -> no duplicate issuing), inserts
#     the transaction and flips the book to 'Issued'.
#
# Presentation only: verification and the database write live in the service.
#
# This file also contains ReturnBookView (below): search active loans, select
# one, and return it (updates return date + status, frees the book).
# ============================================================================

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, timedelta

from config.settings import LOAN_PERIOD_DAYS
from services.book_service import BookService
from services.borrower_service import BorrowerService
from services.circulation_service import CirculationService


class IssueBookView(ttk.Frame):
    """A framed 'Issue Book' form."""

    HEADER_BG = "#2c3e50"
    HEADER_FG = "#ffffff"

    def __init__(self, parent, book_service=None, borrower_service=None, circulation_service=None):
        super().__init__(parent, padding=0)
        self.book_service = book_service or BookService()
        self.borrower_service = borrower_service or BorrowerService()
        self.circulation = circulation_service or CirculationService()

        # Parallel lists so the selected combobox index maps to a real id.
        self._available_books = []
        self._borrowers = []

        self.var_issue = tk.StringVar()
        self.var_expected = tk.StringVar()

        self._build_ui()
        self._load_dropdowns()
        self._set_default_dates()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        self.columnconfigure(0, weight=1)

        # ---- Header --------------------------------------------------------
        header = tk.Frame(self, bg=self.HEADER_BG, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Label(
            header, text="  Issue Book", bg=self.HEADER_BG, fg=self.HEADER_FG,
            font=("Segoe UI", 16, "bold"),
        ).place(relx=0.0, rely=0.5, anchor="w", x=15)

        # ---- Form ----------------------------------------------------------
        form = ttk.Frame(self, padding=25)
        form.grid(row=1, column=0, sticky="nsew", padx=30, pady=20)
        form.columnconfigure(1, weight=1)

        def label(row, text, required=False):
            wrap = ttk.Frame(form)
            wrap.grid(row=row, column=0, sticky="e", pady=10, padx=(0, 12))
            ttk.Label(wrap, text=text, font=("Segoe UI", 10)).pack(side="left")
            if required:
                tk.Label(wrap, text=" *", fg="red").pack(side="left")

        # Book (available only)
        label(0, "Book", required=True)
        self.cmb_book = ttk.Combobox(form, state="readonly", font=("Segoe UI", 10))
        self.cmb_book.grid(row=0, column=1, sticky="ew", pady=10)

        # Borrower
        label(1, "Borrower", required=True)
        self.cmb_borrower = ttk.Combobox(form, state="readonly", font=("Segoe UI", 10))
        self.cmb_borrower.grid(row=1, column=1, sticky="ew", pady=10)

        # Issue date
        label(2, "Issue Date", required=True)
        issue_wrap = ttk.Frame(form)
        issue_wrap.grid(row=2, column=1, sticky="ew", pady=10)
        ttk.Entry(issue_wrap, textvariable=self.var_issue, width=18).pack(side="left")
        ttk.Label(issue_wrap, text="  (YYYY-MM-DD)", foreground="#888").pack(side="left")

        # Expected return date
        label(3, "Expected Return Date", required=True)
        exp_wrap = ttk.Frame(form)
        exp_wrap.grid(row=3, column=1, sticky="ew", pady=10)
        ttk.Entry(exp_wrap, textvariable=self.var_expected, width=18).pack(side="left")
        ttk.Label(exp_wrap, text=f"  (default: +{LOAN_PERIOD_DAYS} days)",
                  foreground="#888").pack(side="left")

        # Status line
        self.lbl_status = ttk.Label(self, text="", font=("Segoe UI", 10, "bold"))
        self.lbl_status.grid(row=2, column=0, sticky="w", padx=55)

        # ---- Buttons -------------------------------------------------------
        btns = ttk.Frame(self, padding=(30, 5, 30, 25))
        btns.grid(row=3, column=0, sticky="ew")
        ttk.Button(btns, text="Issue", command=self._on_issue).pack(side="left")
        ttk.Button(btns, text="Clear", command=self._on_clear).pack(side="left", padx=10)
        ttk.Button(btns, text="Refresh Lists", command=self._on_refresh).pack(side="right")

    # ------------------------------------------------------------------ #
    # Data loading
    # ------------------------------------------------------------------ #
    def _load_dropdowns(self):
        """Populate the book (available only) and borrower dropdowns."""
        # Available books = catalog minus anything not 'Available'.
        books_result = self.book_service.get_all_books()
        self._available_books = [
            b for b in (books_result["data"] or []) if b.is_available()
        ] if books_result["success"] else []
        self.cmb_book["values"] = [
            f"{b.title} — {b.author or 'Unknown'}" for b in self._available_books
        ]
        self.cmb_book.set("")

        borrowers_result = self.borrower_service.get_all_borrowers()
        self._borrowers = borrowers_result["data"] or [] if borrowers_result["success"] else []
        self.cmb_borrower["values"] = [
            f"{p.name}" + (f" — {p.phone}" if p.phone else "") for p in self._borrowers
        ]
        self.cmb_borrower.set("")

        # Helpful hints when nothing is available.
        if not self._available_books:
            self._set_status("No available books to issue.", error=True)
        elif not self._borrowers:
            self._set_status("No borrowers registered yet.", error=True)
        else:
            self._set_status("")

    def _set_default_dates(self):
        today = date.today()
        self.var_issue.set(today.isoformat())
        self.var_expected.set((today + timedelta(days=LOAN_PERIOD_DAYS)).isoformat())

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    def _on_issue(self):
        book_index = self.cmb_book.current()
        borrower_index = self.cmb_borrower.current()

        if book_index < 0:
            self._set_status("Please select a book.", error=True)
            return
        if borrower_index < 0:
            self._set_status("Please select a borrower.", error=True)
            return

        book = self._available_books[book_index]
        borrower = self._borrowers[borrower_index]

        result = self.circulation.issue_book(
            book_id=book.book_id,
            borrower_id=borrower.borrower_id,
            issue_date=self.var_issue.get().strip(),
            expected_return_date=self.var_expected.get().strip(),
        )

        if result["success"]:
            self._set_status(result["message"], error=False)
            messagebox.showinfo("Issued", result["message"])
            # Reload so the just-issued book leaves the "available" list.
            self._load_dropdowns()
            self._set_default_dates()
        else:
            self._set_status(result["message"], error=True)
            messagebox.showerror("Error", result["message"])

    def _on_clear(self):
        self.cmb_book.set("")
        self.cmb_borrower.set("")
        self._set_default_dates()
        self._set_status("")

    def _on_refresh(self):
        self._load_dropdowns()
        self._set_default_dates()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _set_status(self, message, error=False):
        colour = "#c0392b" if error else "#27ae60"
        self.lbl_status.config(text=message, foreground=colour)


class ReturnBookView(ttk.Frame):
    """
    A framed 'Return Book' screen: a searchable table of books currently out,
    with a Return action.
    """

    HEADER_BG = "#2c3e50"
    HEADER_FG = "#ffffff"
    ROW_ODD = "#ffffff"
    ROW_EVEN = "#f4f6f7"

    COLUMNS = (
        ("book", "Book", 230, True),
        ("borrower", "Borrower", 170, True),
        ("issued", "Issued On", 110, False),
        ("due", "Due Date", 110, False),
        ("state", "State", 90, False),
    )

    def __init__(self, parent, circulation_service=None):
        super().__init__(parent, padding=0)
        self.circulation = circulation_service or CirculationService()
        self._loans_by_txid = {}
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = tk.Frame(self, bg=self.HEADER_BG, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Label(
            header, text="  Return Book", bg=self.HEADER_BG, fg=self.HEADER_FG,
            font=("Segoe UI", 16, "bold"),
        ).place(relx=0.0, rely=0.5, anchor="w", x=15)

        # Toolbar: search active loans + actions.
        toolbar = ttk.Frame(self, padding=(15, 12))
        toolbar.grid(row=1, column=0, sticky="ew")
        toolbar.columnconfigure(1, weight=1)
        ttk.Label(toolbar, text="Search:").grid(row=0, column=0, padx=(0, 6))
        self.var_search = tk.StringVar()
        entry = ttk.Entry(toolbar, textvariable=self.var_search, width=30)
        entry.grid(row=0, column=1, sticky="w")
        entry.bind("<Return>", lambda e: self._on_search())
        ttk.Button(toolbar, text="Search", command=self._on_search).grid(row=0, column=2, padx=4)
        ttk.Button(toolbar, text="Refresh", command=self.refresh).grid(row=0, column=3, padx=4)
        ttk.Button(toolbar, text="Return Selected", command=self._on_return).grid(row=0, column=4, padx=4)

        # Table of active loans.
        wrap = ttk.Frame(self, padding=(15, 0, 15, 10))
        wrap.grid(row=2, column=0, sticky="nsew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        col_ids = [c[0] for c in self.COLUMNS]
        self.tree = ttk.Treeview(wrap, columns=col_ids, show="headings", selectmode="browse")
        for col_id, heading, width, stretch in self.COLUMNS:
            self.tree.heading(col_id, text=heading)
            self.tree.column(col_id, width=width, stretch=stretch, anchor="w")
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.tree.tag_configure("odd", background=self.ROW_ODD)
        self.tree.tag_configure("even", background=self.ROW_EVEN)
        self.tree.tag_configure("overdue", foreground="#c0392b")  # red for late
        self.tree.bind("<Double-1>", lambda e: self._on_return())

        self.lbl_status = ttk.Label(self, text="", padding=(15, 4), foreground="#555")
        self.lbl_status.grid(row=3, column=0, sticky="w")

    # ------------------------------------------------------------------ #
    # Data loading
    # ------------------------------------------------------------------ #
    def refresh(self):
        self.var_search.set("")
        self._load(self.circulation.get_active_loans())

    def _on_search(self):
        self._load(self.circulation.get_active_loans(self.var_search.get().strip()))

    def _load(self, result):
        self.tree.delete(*self.tree.get_children())
        self._loans_by_txid.clear()

        if not result["success"]:
            self.lbl_status.config(text=result["message"], foreground="#c0392b")
            return

        for index, loan in enumerate(result["data"] or []):
            self._loans_by_txid[loan["transaction_id"]] = loan
            base_tag = "even" if index % 2 else "odd"
            tags = (base_tag, "overdue") if loan["overdue"] else (base_tag,)
            self.tree.insert(
                "", "end",
                iid=str(loan["transaction_id"]),
                values=(
                    loan["book_title"],
                    loan["borrower_name"],
                    loan["issue_date"] or "",
                    loan["expected_return_date"] or "",
                    "OVERDUE" if loan["overdue"] else "On time",
                ),
                tags=tags,
            )
        self.lbl_status.config(text=result["message"], foreground="#555")

    # ------------------------------------------------------------------ #
    # Return action
    # ------------------------------------------------------------------ #
    def _on_return(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("No selection", "Please select a book to return.")
            return
        loan = self._loans_by_txid.get(int(selection[0]))
        if loan is None:
            return
        if not messagebox.askyesno(
            "Confirm return",
            f"Return '{loan['book_title']}' from '{loan['borrower_name']}'?",
        ):
            return
        result = self.circulation.return_book(loan["transaction_id"])
        if result["success"]:
            messagebox.showinfo("Returned", result["message"])
            self.refresh()
        else:
            messagebox.showerror("Error", result["message"])


# ----------------------------------------------------------------------------
# Standalone preview:  python -m ui.circulation_view
# Shows Issue and Return screens in two tabs for convenience.
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Circulation — Preview")
    root.geometry("760x520")
    notebook = ttk.Notebook(root)
    notebook.add(IssueBookView(notebook), text="Issue Book")
    notebook.add(ReturnBookView(notebook), text="Return Book")
    notebook.pack(fill="both", expand=True)
    root.mainloop()
