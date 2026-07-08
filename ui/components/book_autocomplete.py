# ============================================================================
# ui/components/book_autocomplete.py
# ----------------------------------------------------------------------------
# BOOK AUTOCOMPLETE — a reusable "Google-style" title search widget.
#
# It is a small ttk.Frame containing a search entry plus a suggestion dropdown.
# Drop it into any form where a book must be chosen (e.g. the Issue screen).
#
# Features:
#   - Placeholder text; live suggestions as you type (debounced ~275 ms).
#   - Title-only, case-insensitive matching (start / any word / partial).
#   - Ranked results: exact > starts-with > word-starts-with > contains, max 8.
#   - Keyboard nav (Up/Down/Enter/Esc), click to select, "No books found".
#   - Optional filter_fn to restrict candidates (e.g. only available books).
#
# The chosen Book is exposed as `self.selected_book` (None until one is picked,
# and reset to None whenever the text changes) and an optional on_select
# callback fires when a book is chosen. Searching runs in
# BookService.search_books_by_title (Title column only); ranking is done here.
# ============================================================================

import tkinter as tk
from tkinter import ttk

from services.book_service import BookService
from ui import theme


class BookAutocomplete(ttk.Frame):
    """A reusable autocomplete field for picking a book by title."""

    DEBOUNCE_MS = 275
    MAX_SUGGESTIONS = 8

    def __init__(self, parent, book_service=None, on_select=None, filter_fn=None,
                 placeholder="Search books by title..."):
        super().__init__(parent)
        self.service = book_service or BookService()
        self.on_select = on_select          # callback(book) when one is chosen
        self.filter_fn = filter_fn          # optional predicate to keep a book
        self.placeholder = placeholder

        self.selected_book = None           # the currently chosen Book (or None)

        self.var = tk.StringVar()
        self._suppress = False
        self._placeholder_on = False
        self._after_id = None
        self._suggestions = []
        self._sel_index = -1

        self._build()
        self._set_placeholder()

    # ------------------------------------------------------------------ #
    # Widget construction
    # ------------------------------------------------------------------ #
    def _build(self):
        self.columnconfigure(0, weight=1)

        self.entry = ttk.Entry(self, textvariable=self.var, font=("Segoe UI", 10))
        self.entry.grid(row=0, column=0, sticky="ew")
        self.var.trace_add("write", self._on_change)
        self.entry.bind("<Down>", self._on_down)
        self.entry.bind("<Up>", self._on_up)
        self.entry.bind("<Return>", self._on_return)
        self.entry.bind("<Escape>", lambda e: self._hide())
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)

        self.listbox = tk.Listbox(
            self, height=self.MAX_SUGGESTIONS, activestyle="none",
            font=("Segoe UI", 10), relief="flat", highlightthickness=1,
            highlightbackground="#dfe4e6",
            selectbackground=theme.ACCENT, selectforeground="#ffffff",
        )
        self.listbox.grid(row=1, column=0, sticky="ew", pady=(1, 0))
        self.listbox.bind("<ButtonRelease-1>", self._on_click)
        self.listbox.grid_remove()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def clear(self):
        """Reset the field to its empty/placeholder state."""
        self._hide()
        self.selected_book = None
        self._set_placeholder()

    # ------------------------------------------------------------------ #
    # Placeholder
    # ------------------------------------------------------------------ #
    def _set_placeholder(self):
        self._suppress = True
        self.var.set(self.placeholder)
        self.entry.configure(foreground="#9aa4a9")
        self._placeholder_on = True
        self._suppress = False

    def _clear_placeholder(self):
        if self._placeholder_on:
            self._suppress = True
            self.var.set("")
            self.entry.configure(foreground="#2c3e50")
            self._placeholder_on = False
            self._suppress = False

    # ------------------------------------------------------------------ #
    # Live search (debounced)
    # ------------------------------------------------------------------ #
    def _on_change(self, *_args):
        if self._suppress or self._placeholder_on:
            return
        # Typing invalidates any previous choice until a suggestion is picked.
        self.selected_book = None
        if self._after_id is not None:
            self.after_cancel(self._after_id)
        self._after_id = self.after(self.DEBOUNCE_MS, self._run_search)

    def _run_search(self):
        self._after_id = None
        query = self.var.get().strip()
        if not query:
            self._hide()
            return
        result = self.service.search_books_by_title(query)
        if not result["success"]:
            self._hide()
            return
        books = result["data"] or []
        if self.filter_fn is not None:
            books = [b for b in books if self.filter_fn(b)]
        self._suggestions = self._rank(books, query)
        self._populate(query)

    @staticmethod
    def _rank(books, query):
        """exact > starts-with > word-starts-with > contains; then alphabetical."""
        q = query.lower()

        def score(book):
            title = (book.title or "").lower()
            if title == q:
                return 0
            if title.startswith(q):
                return 1
            if any(word.startswith(q) for word in title.split()):
                return 2
            return 3

        ranked = sorted(books, key=lambda b: (score(b), (b.title or "").lower()))
        return ranked[:BookAutocomplete.MAX_SUGGESTIONS]

    def _populate(self, _query):
        self.listbox.delete(0, "end")
        self._sel_index = -1
        if not self._suggestions:
            self.listbox.insert("end", "No books found")
            self.listbox.itemconfigure(0, foreground="#c0392b")
            self._show()
            return
        for book in self._suggestions:
            self.listbox.insert("end", book.title)
        self._show()

    # ------------------------------------------------------------------ #
    # Dropdown show / hide
    # ------------------------------------------------------------------ #
    def _show(self):
        self.listbox.grid()

    def _hide(self):
        self.listbox.grid_remove()
        self._sel_index = -1

    def _open(self):
        return bool(self.listbox.winfo_ismapped())

    # ------------------------------------------------------------------ #
    # Keyboard navigation
    # ------------------------------------------------------------------ #
    def _on_down(self, _event):
        if self._open() and self._suggestions:
            self._move(1)
        return "break"

    def _on_up(self, _event):
        if self._open() and self._suggestions:
            self._move(-1)
        return "break"

    def _move(self, delta):
        count = len(self._suggestions)
        self._sel_index = (self._sel_index + delta) % count
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(self._sel_index)
        self.listbox.activate(self._sel_index)
        self.listbox.see(self._sel_index)

    def _on_return(self, _event):
        if self._open() and self._suggestions:
            self._select(self._sel_index if self._sel_index >= 0 else 0)
        return "break"

    def _on_click(self, event):
        if not self._suggestions:
            return
        index = self.listbox.nearest(event.y)
        if 0 <= index < len(self._suggestions):
            self._select(index)

    # ------------------------------------------------------------------ #
    # Selection
    # ------------------------------------------------------------------ #
    def _select(self, index):
        book = self._suggestions[index]
        self._suppress = True
        self.var.set(book.title)
        self.entry.configure(foreground="#2c3e50")
        self._placeholder_on = False
        self._suppress = False

        self.selected_book = book
        self._hide()
        self.entry.focus_set()
        self.entry.icursor("end")
        if callable(self.on_select):
            self.on_select(book)

    # ------------------------------------------------------------------ #
    # Focus
    # ------------------------------------------------------------------ #
    def _on_focus_in(self, _event):
        self._clear_placeholder()
        if self.var.get().strip() and self.selected_book is None:
            self._run_search()

    def _on_focus_out(self, _event):
        self.after(150, self._maybe_close)

    def _maybe_close(self):
        focused = self.focus_get()
        if focused is self.listbox or focused is self.entry:
            return
        self._hide()
        if not self.var.get().strip():
            self._set_placeholder()
