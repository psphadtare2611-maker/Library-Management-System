# ============================================================================
# ui/book_view.py
# ----------------------------------------------------------------------------
# BOOK LIST SCREEN — browse, search, edit and remove the book catalog.
#
# Shows all books in a professional ttk.Treeview with:
#   - Search box (Title / Author / Category)
#   - Refresh button
#   - Update button + double-click to edit (opens a pre-filled dialog)
#   - Delete button (soft delete via BookService)
#   - Sortable columns (click a header to sort, click again to reverse)
#   - Responsive layout (the table grows/shrinks with the window)
#
# The hidden BookID is stored as each row's internal id (iid), so the screen
# can act on the correct book without ever displaying the id to the user.
#
# Presentation only: all data work goes through BookService.
# ============================================================================

import tkinter as tk
from tkinter import ttk, messagebox

from models.book import Book
from services.book_service import BookService
from ui import theme


class BookListView(ttk.Frame):
    """A framed, sortable list of all books with edit/delete actions."""

    # Shared palette (see ui/theme.py) — kept as class attributes so the rest
    # of the screen can reference self.HEADER_BG etc. as before.
    HEADER_BG = theme.HEADER_BG
    HEADER_FG = theme.HEADER_FG
    ROW_ODD = theme.ROW_ODD
    ROW_EVEN = theme.ROW_EVEN

    # (column id, heading text, width, stretch?)
    COLUMNS = (
        ("title", "Title", 220, True),
        ("author", "Author", 160, True),
        ("category", "Category", 120, False),
        ("purchase", "Purchase Date", 110, False),
        ("status", "Status", 90, False),
        ("remarks", "Remarks", 200, True),
    )

    def __init__(self, parent, service=None):
        super().__init__(parent, padding=0)
        self.service = service or BookService()

        # Keep the loaded Book objects by id, so editing can pre-fill from the
        # real object instead of re-parsing table text.
        self._books_by_id = {}
        # Remembers the sort direction per column for toggling.
        self._sort_desc = {}

        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        # Make the table row/column stretch with the window (responsive).
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ---- Header bar ----------------------------------------------------
        header = tk.Frame(self, bg=self.HEADER_BG, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Label(
            header, text="  Book Catalog", bg=self.HEADER_BG, fg=self.HEADER_FG,
            font=("Segoe UI", 16, "bold"),
        ).place(relx=0.0, rely=0.5, anchor="w", x=15)

        # ---- Toolbar (search + actions) -----------------------------------
        toolbar = ttk.Frame(self, padding=(15, 12))
        toolbar.grid(row=1, column=0, sticky="ew")
        toolbar.columnconfigure(1, weight=1)

        ttk.Label(toolbar, text="Search:").grid(row=0, column=0, padx=(0, 6))
        self.var_search = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.var_search, width=30)
        search_entry.grid(row=0, column=1, sticky="w")
        search_entry.bind("<Return>", lambda e: self._on_search())  # Enter = search

        ttk.Button(toolbar, text="Search", command=self._on_search).grid(row=0, column=2, padx=4)
        ttk.Button(toolbar, text="Refresh", command=self._on_refresh).grid(row=0, column=3, padx=4)
        ttk.Button(toolbar, text="Update", command=self._on_update).grid(row=0, column=4, padx=4)
        ttk.Button(toolbar, text="Delete", command=self._on_delete,
                   style="Danger.TButton").grid(row=0, column=5, padx=4)

        # ---- Treeview + scrollbars ----------------------------------------
        table_wrap = ttk.Frame(self, padding=(15, 0, 15, 10))
        table_wrap.grid(row=2, column=0, sticky="nsew")
        table_wrap.rowconfigure(0, weight=1)
        table_wrap.columnconfigure(0, weight=1)

        self._apply_style()

        col_ids = [c[0] for c in self.COLUMNS]
        self.tree = ttk.Treeview(
            table_wrap, columns=col_ids, show="headings", selectmode="browse"
        )
        for col_id, heading, width, stretch in self.COLUMNS:
            # Clicking a heading sorts by that column.
            self.tree.heading(col_id, text=heading,
                              command=lambda c=col_id: self._sort_by(c))
            self.tree.column(col_id, width=width, stretch=stretch, anchor="w")

        vsb = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_wrap, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # Alternating row colours for readability.
        self.tree.tag_configure("odd", background=self.ROW_ODD)
        self.tree.tag_configure("even", background=self.ROW_EVEN)

        # Double-click a row to edit it.
        self.tree.bind("<Double-1>", self._on_double_click)

        # ---- Status line ---------------------------------------------------
        self.lbl_status = ttk.Label(self, text="", padding=(15, 4), foreground="#555")
        self.lbl_status.grid(row=3, column=0, sticky="w")

    def _apply_style(self):
        """Apply the shared professional Treeview styling (see ui/theme.py)."""
        theme.apply_treeview_style()

    # ------------------------------------------------------------------ #
    # Data loading
    # ------------------------------------------------------------------ #
    def refresh(self):
        """Reload the full catalog and clear any search text."""
        self.var_search.set("")
        self._load(self.service.get_all_books())

    def _load(self, result):
        """Populate the table from a BookService response dict."""
        # Clear existing rows.
        self.tree.delete(*self.tree.get_children())
        self._books_by_id.clear()

        if not result["success"]:
            self._set_status(result["message"], error=True)
            return

        books = result["data"] or []
        for index, book in enumerate(books):
            self._books_by_id[book.book_id] = book
            tag = "even" if index % 2 else "odd"
            self.tree.insert(
                "", "end",
                iid=str(book.book_id),          # hidden id lives here
                values=(
                    book.title,
                    book.author or "",
                    book.category or "",
                    book.purchase_date or "",
                    book.status,
                    book.remarks or "",
                ),
                tags=(tag,),
            )
        self._set_status(result["message"])

    # ------------------------------------------------------------------ #
    # Toolbar actions
    # ------------------------------------------------------------------ #
    def _on_search(self):
        keyword = self.var_search.get().strip()
        if not keyword:
            self._load(self.service.get_all_books())
        else:
            self._load(self.service.search_book(keyword))

    def _on_refresh(self):
        self.refresh()

    def _on_update(self):
        book = self._selected_book()
        if book is None:
            messagebox.showwarning("No selection", "Please select a book to update.")
            return
        self._open_edit_dialog(book)

    def _on_delete(self):
        book = self._selected_book()
        if book is None:
            messagebox.showwarning("No selection", "Please select a book to delete.")
            return
        if not messagebox.askyesno(
            "Confirm delete", f"Remove '{book.title}' from the library?"
        ):
            return
        result = self.service.delete_book(book.book_id)
        if result["success"]:
            messagebox.showinfo("Removed", result["message"])
            self.refresh()
        else:
            messagebox.showerror("Error", result["message"])

    def _on_double_click(self, _event):
        book = self._selected_book()
        if book is not None:
            self._open_edit_dialog(book)

    # ------------------------------------------------------------------ #
    # Column sorting
    # ------------------------------------------------------------------ #
    def _sort_by(self, col):
        """Sort rows by a column; clicking the same header reverses order."""
        descending = self._sort_desc.get(col, False)
        rows = [(self.tree.set(iid, col), iid) for iid in self.tree.get_children()]
        # Case-insensitive; ISO dates sort correctly as text.
        rows.sort(key=lambda pair: pair[0].lower(), reverse=descending)
        for position, (_value, iid) in enumerate(rows):
            self.tree.move(iid, "", position)
            # Re-stripe alternating colours after the move.
            self.tree.item(iid, tags=("even" if position % 2 else "odd",))
        self._sort_desc[col] = not descending  # toggle for next click

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _selected_book(self):
        """Return the Book for the selected row, or None if nothing selected."""
        selection = self.tree.selection()
        if not selection:
            return None
        book_id = int(selection[0])
        return self._books_by_id.get(book_id)

    def _set_status(self, message, error=False):
        self.lbl_status.config(text=message, foreground="#c0392b" if error else "#555")

    # ------------------------------------------------------------------ #
    # Edit dialog (used by Update button and double-click)
    # ------------------------------------------------------------------ #
    def _open_edit_dialog(self, book):
        dialog = _EditBookDialog(self, book, self.service, on_saved=self.refresh)
        dialog.grab_set()   # modal: block the list until the dialog closes


class _EditBookDialog(tk.Toplevel):
    """A modal pop-up form for editing an existing book."""

    def __init__(self, parent, book, service, on_saved=None):
        super().__init__(parent)
        self.title("Edit Book")
        self.geometry("460x400")
        self.resizable(False, False)
        self.service = service
        self.book = book
        self.on_saved = on_saved

        self.var_title = tk.StringVar(value=book.title)
        self.var_author = tk.StringVar(value=book.author or "")
        self.var_category = tk.StringVar(value=book.category or "")
        self.var_purchase = tk.StringVar(value=str(book.purchase_date) if book.purchase_date else "")
        self.var_status = tk.StringVar(value=book.status)

        self._build(book)

    def _build(self, book):
        frm = ttk.Frame(self, padding=20)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)

        def row(r, text, widget):
            ttk.Label(frm, text=text).grid(row=r, column=0, sticky="e", pady=6, padx=(0, 10))
            widget.grid(row=r, column=1, sticky="ew", pady=6)

        row(0, "Title *", ttk.Entry(frm, textvariable=self.var_title))
        row(1, "Author", ttk.Entry(frm, textvariable=self.var_author))
        row(2, "Category", ttk.Entry(frm, textvariable=self.var_category))
        row(3, "Purchase Date", ttk.Entry(frm, textvariable=self.var_purchase))
        row(4, "Status", ttk.Combobox(
            frm, textvariable=self.var_status, state="readonly",
            values=list(Book.VALID_STATUSES),
        ))

        ttk.Label(frm, text="Remarks").grid(row=5, column=0, sticky="ne", pady=6, padx=(0, 10))
        self.txt_remarks = tk.Text(frm, height=4, width=30, wrap="word")
        self.txt_remarks.insert("1.0", book.remarks or "")
        self.txt_remarks.grid(row=5, column=1, sticky="ew", pady=6)

        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, columnspan=2, sticky="e", pady=(15, 0))
        ttk.Button(btns, text="Save", command=self._save,
                   style="Primary.TButton").pack(side="left", padx=5)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left")

    def _save(self):
        title = self.var_title.get().strip()
        if not title:
            messagebox.showerror("Error", "Title is required.", parent=self)
            return
        try:
            updated = Book(
                book_id=self.book.book_id,   # keep the hidden id
                title=title,
                author=self.var_author.get().strip() or None,
                category=self.var_category.get().strip() or None,
                purchase_date=self.var_purchase.get().strip() or None,
                status=self.var_status.get(),
                remarks=self.txt_remarks.get("1.0", "end").strip() or None,
            )
        except ValueError as validation_error:
            messagebox.showerror("Error", str(validation_error), parent=self)
            return

        result = self.service.update_book(updated)
        if result["success"]:
            messagebox.showinfo("Saved", result["message"], parent=self)
            if callable(self.on_saved):
                self.on_saved()
            self.destroy()
        else:
            messagebox.showerror("Error", result["message"], parent=self)


# ----------------------------------------------------------------------------
# Standalone preview:  python -m ui.book_view
# (Loading rows needs SQL Server; without it the status line shows the error.)
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Book Catalog — Preview")
    root.geometry("900x560")
    view = BookListView(root)
    view.pack(fill="both", expand=True)
    root.mainloop()
