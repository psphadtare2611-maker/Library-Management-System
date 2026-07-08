# ============================================================================
# ui/add_book_view.py
# ----------------------------------------------------------------------------
# ADD BOOK SCREEN — a professional Tkinter form for adding a new book.
#
# Fields : Title (required), Author, Category, Purchase Date, Remarks.
#          (No ISBN — this is a domestic library; ISBN was dropped from the
#           model and database, so there is nothing to enter or check.)
# Buttons: Save  -> validate + BookService.add_book()
#          Clear -> reset the form
#          Back  -> navigation hook (NOT wired yet, on purpose)
#
# This screen is PRESENTATION only: it collects input, asks BookService to do
# the work, and shows the success/error message it gets back. It contains no
# SQL and no business rules.
# ============================================================================

import tkinter as tk
from tkinter import ttk, messagebox

from models.book import Book
from services.book_service import BookService
from ui import theme


class AddBookView(ttk.Frame):
    """A framed 'Add Book' form that can be dropped into the main window."""

    # Shared palette (see ui/theme.py).
    HEADER_BG = theme.HEADER_BG
    HEADER_FG = theme.HEADER_FG
    ACCENT = theme.ACCENT

    def __init__(self, parent, service=None, on_back=None):
        """
        parent  : the container widget (root window or content frame).
        service : a BookService instance (injected for testability). If not
                  given, one is created. Building it does NOT open a database
                  connection — that only happens when Save is pressed.
        on_back : optional callback for the Back button. Navigation is not
                  implemented yet, so this is just a placeholder hook.
        """
        super().__init__(parent, padding=0)
        self.service = service or BookService()
        self.on_back = on_back

        # Tkinter variables bound to the entry fields.
        self.var_title = tk.StringVar()
        self.var_author = tk.StringVar()
        self.var_category = tk.StringVar()
        self.var_purchase = tk.StringVar()

        self._build_ui()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        """Lay out the header, the form fields, and the action buttons."""
        self.columnconfigure(0, weight=1)

        # ---- Header bar ----------------------------------------------------
        header = tk.Frame(self, bg=self.HEADER_BG, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Label(
            header,
            text="  Add New Book",
            bg=self.HEADER_BG,
            fg=self.HEADER_FG,
            font=("Segoe UI", 16, "bold"),
        ).place(relx=0.0, rely=0.5, anchor="w", x=15)

        # ---- Form card -----------------------------------------------------
        form = ttk.Frame(self, padding=25)
        form.grid(row=1, column=0, sticky="nsew", padx=30, pady=25)
        form.columnconfigure(1, weight=1)

        label_font = ("Segoe UI", 10)
        entry_font = ("Segoe UI", 10)

        # Title (required)
        self._field_label(form, 0, "Title", required=True, font=label_font)
        ttk.Entry(form, textvariable=self.var_title, font=entry_font, width=40).grid(
            row=0, column=1, sticky="ew", pady=8, padx=(10, 0)
        )

        # Author
        self._field_label(form, 1, "Author", font=label_font)
        ttk.Entry(form, textvariable=self.var_author, font=entry_font, width=40).grid(
            row=1, column=1, sticky="ew", pady=8, padx=(10, 0)
        )

        # Category
        self._field_label(form, 2, "Category", font=label_font)
        ttk.Entry(form, textvariable=self.var_category, font=entry_font, width=40).grid(
            row=2, column=1, sticky="ew", pady=8, padx=(10, 0)
        )

        # Purchase Date (with format hint)
        self._field_label(form, 3, "Purchase Date", font=label_font)
        date_wrap = ttk.Frame(form)
        date_wrap.grid(row=3, column=1, sticky="ew", pady=8, padx=(10, 0))
        ttk.Entry(date_wrap, textvariable=self.var_purchase, font=entry_font, width=18).pack(
            side="left"
        )
        ttk.Label(date_wrap, text="  (YYYY-MM-DD, optional)", foreground="#888").pack(
            side="left"
        )

        # Remarks (multi-line)
        self._field_label(form, 4, "Remarks", font=label_font, anchor_n=True)
        self.txt_remarks = tk.Text(form, height=4, width=40, font=entry_font, wrap="word")
        self.txt_remarks.grid(row=4, column=1, sticky="ew", pady=8, padx=(10, 0))

        # ---- Status message line ------------------------------------------
        self.lbl_status = ttk.Label(self, text="", font=("Segoe UI", 10, "bold"))
        self.lbl_status.grid(row=2, column=0, sticky="w", padx=55)

        # ---- Buttons -------------------------------------------------------
        btns = ttk.Frame(self, padding=(30, 10, 30, 25))
        btns.grid(row=3, column=0, sticky="ew")
        ttk.Button(btns, text="Save", command=self._on_save,
                   style="Primary.TButton").pack(side="left")
        ttk.Button(btns, text="Clear", command=self._on_clear).pack(side="left", padx=10)
        ttk.Button(btns, text="Back", command=self._on_back).pack(side="right")

    def _field_label(self, parent, row, text, required=False, font=None, anchor_n=False):
        """Create a right-aligned field label, with a red '*' if required."""
        wrap = ttk.Frame(parent)
        wrap.grid(row=row, column=0, sticky="ne" if anchor_n else "e", pady=8)
        ttk.Label(wrap, text=text, font=font).pack(side="left")
        if required:
            tk.Label(wrap, text=" *", fg="red", font=font).pack(side="left")

    # ------------------------------------------------------------------ #
    # Button actions
    # ------------------------------------------------------------------ #
    def _on_save(self):
        """Validate the form, build a Book, and hand it to BookService."""
        title = self.var_title.get().strip()

        # --- Required-field validation -------------------------------------
        if not title:
            self._show_error("Title is required.")
            return

        # --- Build the Book (its constructor validates date/status) --------
        try:
            book = Book(
                title=title,
                author=self.var_author.get().strip() or None,
                category=self.var_category.get().strip() or None,
                purchase_date=self.var_purchase.get().strip() or None,
                remarks=self.txt_remarks.get("1.0", "end").strip() or None,
            )
        except ValueError as validation_error:
            # e.g. bad date format or a future purchase date.
            self._show_error(str(validation_error))
            return

        # --- Persist via the service ---------------------------------------
        result = self.service.add_book(book)
        if result["success"]:
            self._show_success(result["message"])
            messagebox.showinfo("Success", result["message"])
            self._on_clear()
        else:
            self._show_error(result["message"])
            messagebox.showerror("Error", result["message"])

    def _on_clear(self):
        """Reset every field back to empty."""
        self.var_title.set("")
        self.var_author.set("")
        self.var_category.set("")
        self.var_purchase.set("")
        self.txt_remarks.delete("1.0", "end")
        self.lbl_status.config(text="")

    def _on_back(self):
        """
        Navigation is intentionally NOT implemented yet. If a callback was
        supplied, call it; otherwise just tell the user it's not wired.
        """
        if callable(self.on_back):
            self.on_back()
        else:
            messagebox.showinfo("Back", "Navigation is not implemented yet.")

    # ------------------------------------------------------------------ #
    # Status helpers
    # ------------------------------------------------------------------ #
    def _show_success(self, message):
        self.lbl_status.config(text=message, foreground="#27ae60")  # green

    def _show_error(self, message):
        self.lbl_status.config(text=message, foreground="#c0392b")  # red


# ----------------------------------------------------------------------------
# Standalone preview: run this file directly to see just the Add Book screen.
#   python -m ui.add_book_view
# (Saving will try to reach SQL Server; without it you'll see an error message,
#  which is the error-handling path working as intended.)
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Add Book — Preview")
    root.geometry("640x520")
    view = AddBookView(root)
    view.pack(fill="both", expand=True)
    root.mainloop()
