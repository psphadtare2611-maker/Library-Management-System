# ============================================================================
# ui/search_view.py
# ----------------------------------------------------------------------------
# UNIVERSAL SEARCH SCREEN — one box to search the whole library.
#
# As the user types, results update INSTANTLY (a short 200 ms debounce keeps
# it from querying on every single keystroke). Matches books (Title, Author,
# Category, Status) and borrowers (Name, Phone, Email) and shows them together
# in one Treeview.
#
# Presentation only: all searching happens in SearchService.
# ============================================================================

import tkinter as tk
from tkinter import ttk

from services.search_service import SearchService
from ui import theme


class UniversalSearchView(ttk.Frame):
    """A single search box with live, cross-table results."""

    # Shared palette (see ui/theme.py).
    HEADER_BG = theme.HEADER_BG
    HEADER_FG = theme.HEADER_FG
    ROW_ODD = theme.ROW_ODD
    ROW_EVEN = theme.ROW_EVEN
    DEBOUNCE_MS = 200

    COLUMNS = (
        ("type", "Type", 90, False),
        ("name", "Name / Title", 240, True),
        ("details", "Details", 300, True),
        ("status", "Status", 110, False),
    )

    def __init__(self, parent, service=None):
        super().__init__(parent, padding=0)
        self.service = service or SearchService()
        self._after_id = None

        self.var_query = tk.StringVar()
        # Fire a (debounced) search whenever the text changes.
        self.var_query.trace_add("write", self._on_change)

        self._build_ui()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ---- Header --------------------------------------------------------
        header = tk.Frame(self, bg=self.HEADER_BG, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Label(
            header, text="  Universal Search", bg=self.HEADER_BG, fg=self.HEADER_FG,
            font=("Segoe UI", 16, "bold"),
        ).place(relx=0.0, rely=0.5, anchor="w", x=15)

        # ---- Search box ----------------------------------------------------
        bar = ttk.Frame(self, padding=(15, 14))
        bar.grid(row=1, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)

        ttk.Label(bar, text="🔍").grid(row=0, column=0, padx=(0, 6))
        entry = ttk.Entry(bar, textvariable=self.var_query, font=("Segoe UI", 12))
        entry.grid(row=0, column=1, sticky="ew")
        entry.focus_set()
        ttk.Label(
            bar, text="Search books & borrowers — title, author, category, name, phone, status",
            foreground="#888",
        ).grid(row=1, column=1, sticky="w", pady=(4, 0))

        # ---- Results Treeview ---------------------------------------------
        self._apply_style()
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
        # Tint by result type so books and borrowers are easy to tell apart.
        self.tree.tag_configure("Book", foreground="#1f5c8b")
        self.tree.tag_configure("Borrower", foreground="#6c3483")

        # ---- Status line ---------------------------------------------------
        self.lbl_status = ttk.Label(self, text="Type to search…", padding=(15, 4),
                                    foreground="#555")
        self.lbl_status.grid(row=3, column=0, sticky="w")

    def _apply_style(self):
        """Apply the shared professional Treeview styling (see ui/theme.py)."""
        theme.apply_treeview_style()

    # ------------------------------------------------------------------ #
    # Live search (debounced)
    # ------------------------------------------------------------------ #
    def _on_change(self, *_args):
        # Cancel any pending search and reschedule — this debounces typing.
        if self._after_id is not None:
            self.after_cancel(self._after_id)
        self._after_id = self.after(self.DEBOUNCE_MS, self._run_search)

    def _run_search(self):
        self._after_id = None
        result = self.service.universal_search(self.var_query.get())
        self._render(result)

    def _render(self, result):
        self.tree.delete(*self.tree.get_children())

        if not result["success"]:
            self.lbl_status.config(text=result["message"], foreground="#c0392b")
            return

        for index, item in enumerate(result["data"]):
            base = "even" if index % 2 else "odd"
            self.tree.insert(
                "", "end",
                values=(item["type"], item["name"], item["details"], item["status"]),
                tags=(base, item["type"]),
            )
        self.lbl_status.config(text=result["message"], foreground="#555")


# ----------------------------------------------------------------------------
# Standalone preview:  python -m ui.search_view
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Universal Search — Preview")
    root.geometry("820x520")
    view = UniversalSearchView(root)
    view.pack(fill="both", expand=True)
    root.mainloop()
