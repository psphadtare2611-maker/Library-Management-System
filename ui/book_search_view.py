# ============================================================================
# ui/book_search_view.py
# ----------------------------------------------------------------------------
# BOOK SEARCH — a single, Google-style autocomplete for finding books by title.
#
# Behaviour (the desktop equivalent of a web autocomplete):
#   - One search box with placeholder "Search books by title...".
#   - Live suggestions appear as you type (debounced ~275 ms) — no Enter needed.
#   - Matching is case-insensitive and matches the start of the title, any word
#     inside it, or a partial word (SQL LIKE '%text%' on the Title column only).
#   - Suggestions are RANKED: exact title > starts-with > word-starts-with >
#     contains. Max 8 shown.
#   - Dropdown: opens while typing, highlights the active row, closes on Esc or
#     an outside click, reopens on focus, shows "No books found" when empty.
#   - Keyboard: Up / Down to move, Enter to select, Esc to close.
#   - Selecting a suggestion fills the box with the title, closes the list, and
#     shows that book's full record in the details panel below.
#
# Presentation only: the search itself runs in BookService.search_books_by_title
# (Title column only); ranking is done here for responsiveness.
# ============================================================================

import tkinter as tk
from tkinter import ttk

from services.book_service import BookService
from ui import theme


class BookSearchView(ttk.Frame):
    """A single intelligent autocomplete search bar for books."""

    HEADER_BG = theme.HEADER_BG
    HEADER_FG = theme.HEADER_FG
    PLACEHOLDER = "Search books by title..."
    DEBOUNCE_MS = 275          # wait this long after the last keystroke before searching
    MAX_SUGGESTIONS = 8

    def __init__(self, parent, service=None):
        super().__init__(parent, padding=0)
        self.service = service or BookService()

        self.var_query = tk.StringVar()
        self._suppress = False          # guards programmatic text changes
        self._placeholder_on = False    # True while the grey placeholder shows
        self._after_id = None           # pending debounced search
        self._suggestions = []          # Book objects currently listed
        self._sel_index = -1            # highlighted row (-1 = none)

        self._build_ui()
        self._set_placeholder()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        # ---- Header --------------------------------------------------------
        header = tk.Frame(self, bg=self.HEADER_BG, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Label(header, text="  Search Books", bg=self.HEADER_BG, fg=self.HEADER_FG,
                 font=("Segoe UI", 16, "bold")).place(relx=0.0, rely=0.5, anchor="w", x=15)

        # ---- Search box ----------------------------------------------------
        bar = ttk.Frame(self, padding=(20, 16, 20, 0))
        bar.grid(row=1, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)
        tk.Label(bar, text="🔍", font=("Segoe UI", 13)).grid(row=0, column=0, padx=(0, 8))
        self.entry = ttk.Entry(bar, textvariable=self.var_query, font=("Segoe UI", 13))
        self.entry.grid(row=0, column=1, sticky="ew", ipady=3)

        # Live search on change; keyboard navigation; focus handling.
        self.var_query.trace_add("write", self._on_change)
        self.entry.bind("<Down>", self._on_down)
        self.entry.bind("<Up>", self._on_up)
        self.entry.bind("<Return>", self._on_return)
        self.entry.bind("<Escape>", lambda e: self._hide_dropdown())
        self.entry.bind("<FocusIn>", self._on_focus_in)
        self.entry.bind("<FocusOut>", self._on_focus_out)

        # ---- Suggestion dropdown (a Listbox shown just under the box) ------
        drop = ttk.Frame(self, padding=(20, 2, 20, 0))
        drop.grid(row=2, column=0, sticky="ew")
        drop.columnconfigure(0, weight=1)
        self._drop_frame = drop
        self.listbox = tk.Listbox(
            drop, height=self.MAX_SUGGESTIONS, activestyle="none",
            font=("Segoe UI", 11), highlightthickness=1,
            highlightbackground="#dfe4e6", relief="flat",
            selectbackground=theme.ACCENT, selectforeground="#ffffff",
        )
        self.listbox.grid(row=0, column=0, sticky="ew")
        self.listbox.bind("<ButtonRelease-1>", self._on_click)
        self.listbox.bind("<Return>", self._on_return)
        self.listbox.bind("<Escape>", lambda e: (self._hide_dropdown(), self.entry.focus_set()))
        drop.grid_remove()   # hidden until there are suggestions

        # ---- Details panel (the selected book's record) -------------------
        card = tk.Frame(self, bg="#ffffff", highlightbackground="#dfe4e6",
                        highlightthickness=1)
        card.grid(row=3, column=0, sticky="nsew", padx=20, pady=16)
        card.columnconfigure(1, weight=1)
        tk.Label(card, text="Book details", bg="#ffffff", fg="#2c3e50",
                 font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2,
                                                      sticky="w", padx=14, pady=(12, 6))
        self._detail_labels = {}
        for i, field in enumerate(("Title", "Author", "Category", "Status",
                                   "Purchase Date", "Remarks"), start=1):
            tk.Label(card, text=field, bg="#ffffff", fg="#7f8c8d",
                     font=("Segoe UI", 10)).grid(row=i, column=0, sticky="ne", padx=(14, 10), pady=3)
            value = tk.Label(card, text="—", bg="#ffffff", fg="#2c3e50",
                             font=("Segoe UI", 10), wraplength=520, justify="left", anchor="w")
            value.grid(row=i, column=1, sticky="w", pady=3)
            self._detail_labels[field] = value

        self.lbl_status = ttk.Label(self, text="", padding=(20, 0, 20, 8), foreground="#888")
        self.lbl_status.grid(row=4, column=0, sticky="w")

    # ------------------------------------------------------------------ #
    # Placeholder handling (Tkinter has no native placeholder)
    # ------------------------------------------------------------------ #
    def _set_placeholder(self):
        self._suppress = True
        self.var_query.set(self.PLACEHOLDER)
        self.entry.configure(foreground="#9aa4a9")
        self._placeholder_on = True
        self._suppress = False

    def _clear_placeholder(self):
        if self._placeholder_on:
            self._suppress = True
            self.var_query.set("")
            self.entry.configure(foreground="#2c3e50")
            self._placeholder_on = False
            self._suppress = False

    # ------------------------------------------------------------------ #
    # Live search (debounced)
    # ------------------------------------------------------------------ #
    def _on_change(self, *_args):
        if self._suppress or self._placeholder_on:
            return
        # Cancel any pending search and reschedule — this is the debounce.
        if self._after_id is not None:
            self.after_cancel(self._after_id)
        self._after_id = self.after(self.DEBOUNCE_MS, self._run_search)

    def _run_search(self):
        self._after_id = None
        query = self.var_query.get().strip()
        if not query:
            self._hide_dropdown()
            return

        result = self.service.search_books_by_title(query)
        if not result["success"]:
            self._set_status(result["message"], error=True)
            self._hide_dropdown()
            return
        self._set_status("")

        # Rank the matches and keep the best few.
        self._suggestions = self._rank(result["data"] or [], query)
        self._populate_dropdown(query)

    @staticmethod
    def _rank(books, query):
        """
        Rank by: exact title, then starts-with, then any-word-starts-with,
        then contains — each group alphabetical. Cap at MAX_SUGGESTIONS.
        """
        q = query.lower()

        def score(book):
            title = (book.title or "").lower()
            if title == q:
                return 0
            if title.startswith(q):
                return 1
            if any(word.startswith(q) for word in title.split()):
                return 2
            return 3   # contains (DB already guaranteed a substring match)

        ranked = sorted(books, key=lambda b: (score(b), (b.title or "").lower()))
        return ranked[:BookSearchView.MAX_SUGGESTIONS]

    def _populate_dropdown(self, query):
        self.listbox.delete(0, "end")
        self._sel_index = -1
        if not self._suggestions:
            # "No books found" — shown but not selectable.
            self.listbox.insert("end", "No books found")
            self.listbox.itemconfigure(0, foreground="#c0392b")
            self._show_dropdown()
            return
        for book in self._suggestions:
            self.listbox.insert("end", book.title)
        self._show_dropdown()

    # ------------------------------------------------------------------ #
    # Dropdown show / hide
    # ------------------------------------------------------------------ #
    def _show_dropdown(self):
        self._drop_frame.grid()

    def _hide_dropdown(self):
        self._drop_frame.grid_remove()
        self._sel_index = -1

    def _dropdown_open(self):
        return bool(self._drop_frame.winfo_ismapped())

    # ------------------------------------------------------------------ #
    # Keyboard navigation
    # ------------------------------------------------------------------ #
    def _on_down(self, _event):
        if not self._dropdown_open() or not self._suggestions:
            return "break"
        self._move(1)
        return "break"   # stop the Entry from moving the caret

    def _on_up(self, _event):
        if not self._dropdown_open() or not self._suggestions:
            return "break"
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
        if not self._dropdown_open() or not self._suggestions:
            return "break"
        # Enter with nothing highlighted selects the top-ranked suggestion.
        index = self._sel_index if self._sel_index >= 0 else 0
        self._select(index)
        return "break"

    def _on_click(self, _event):
        if not self._suggestions:
            return
        index = self.listbox.nearest(_event.y)
        if 0 <= index < len(self._suggestions):
            self._select(index)

    # ------------------------------------------------------------------ #
    # Selecting a suggestion
    # ------------------------------------------------------------------ #
    def _select(self, index):
        book = self._suggestions[index]
        # Fill the box with the chosen title (without re-triggering a search).
        self._suppress = True
        self.var_query.set(book.title)
        self.entry.configure(foreground="#2c3e50")
        self._placeholder_on = False
        self._suppress = False

        self._hide_dropdown()
        self.entry.focus_set()
        self.entry.icursor("end")
        self._show_details(book)

    def _show_details(self, book):
        self._detail_labels["Title"].config(text=book.title or "—")
        self._detail_labels["Author"].config(text=book.author or "—")
        self._detail_labels["Category"].config(text=book.category or "—")
        self._detail_labels["Status"].config(text=book.status or "—")
        self._detail_labels["Purchase Date"].config(
            text=str(book.purchase_date) if book.purchase_date else "—")
        self._detail_labels["Remarks"].config(text=book.remarks or "—")

    # ------------------------------------------------------------------ #
    # Focus handling (reopen on focus, close on outside click)
    # ------------------------------------------------------------------ #
    def _on_focus_in(self, _event):
        self._clear_placeholder()
        # Reopen suggestions if there is already text to match.
        if self.var_query.get().strip():
            self._run_search()

    def _on_focus_out(self, _event):
        # Delay so a click on the listbox is processed before we close.
        self.after(150, self._maybe_close)

    def _maybe_close(self):
        focused = self.focus_get()
        if focused is self.listbox or focused is self.entry:
            return   # focus moved into our own widgets — keep the dropdown open
        self._hide_dropdown()
        if not self.var_query.get().strip():
            self._set_placeholder()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _set_status(self, message, error=False):
        self.lbl_status.config(text=message, foreground="#c0392b" if error else "#888")


# ----------------------------------------------------------------------------
# Standalone preview:  python -m ui.book_search_view
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Search Books — Preview")
    root.geometry("760x560")
    view = BookSearchView(root)
    view.pack(fill="both", expand=True)
    root.mainloop()
