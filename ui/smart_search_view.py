# ============================================================================
# ui/smart_search_view.py
# ----------------------------------------------------------------------------
# SMART SEARCH SCREEN — search books by MEANING (semantic search).
#
# Type a phrase or concept ("wizards and magic", "warrior kings") and the
# screen finds books whose meaning is closest, even if none of those words
# appear in the title. All the ML lives in SemanticSearchService; this screen
# only collects the query and shows ranked results.
#
# Note: the embedding model loads on the FIRST search (a one-time ~1-2s pause);
# every search after that is instant.
# ============================================================================

import tkinter as tk
from tkinter import ttk

from services.semantic_search_service import SemanticSearchService
from ui import theme


class SmartSearchView(ttk.Frame):
    """Meaning-based ("semantic") book search."""

    HEADER_BG = theme.HEADER_BG
    HEADER_FG = theme.HEADER_FG
    ROW_ODD = theme.ROW_ODD
    ROW_EVEN = theme.ROW_EVEN

    COLUMNS = (
        ("match", "Match", 80, False),
        ("title", "Title", 300, True),
        ("author", "Author", 180, True),
        ("category", "Category", 150, False),
    )

    EXAMPLES = "Try:  “wizards and magic”  ·  “warrior kings of India”  ·  “dystopian future”  ·  “classic romance”"

    def __init__(self, parent, service=None):
        super().__init__(parent, padding=0)
        self.service = service or SemanticSearchService()
        self.var_query = tk.StringVar()
        self._build_ui()

    # ------------------------------------------------------------------ #
    # UI
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        header = tk.Frame(self, bg=self.HEADER_BG, height=60)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Label(
            header, text="  Smart Search  (by meaning)", bg=self.HEADER_BG, fg=self.HEADER_FG,
            font=("Segoe UI", 16, "bold"),
        ).place(relx=0.0, rely=0.5, anchor="w", x=15)

        bar = ttk.Frame(self, padding=(15, 14))
        bar.grid(row=1, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)
        ttk.Label(bar, text="🧠").grid(row=0, column=0, padx=(0, 6))
        entry = ttk.Entry(bar, textvariable=self.var_query, font=("Segoe UI", 12))
        entry.grid(row=0, column=1, sticky="ew")
        entry.bind("<Return>", lambda e: self._search())
        entry.focus_set()
        ttk.Button(bar, text="Search", command=self._search).grid(row=0, column=2, padx=(8, 0))

        ttk.Label(self, text=self.EXAMPLES, foreground="#888",
                  padding=(16, 0)).grid(row=2, column=0, sticky="w")

        wrap = ttk.Frame(self, padding=(15, 8, 15, 10))
        wrap.grid(row=3, column=0, sticky="nsew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        theme.apply_treeview_style()
        col_ids = [c[0] for c in self.COLUMNS]
        self.tree = ttk.Treeview(wrap, columns=col_ids, show="headings", selectmode="browse")
        for col_id, heading, width, stretch in self.COLUMNS:
            self.tree.heading(col_id, text=heading)
            self.tree.column(col_id, width=width, stretch=stretch,
                             anchor="center" if col_id == "match" else "w")
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.tag_configure("odd", background=self.ROW_ODD)
        self.tree.tag_configure("even", background=self.ROW_EVEN)

        self.lbl_status = ttk.Label(self, text="Type a concept and press Enter.",
                                    padding=(15, 4), foreground="#555")
        self.lbl_status.grid(row=4, column=0, sticky="w")

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #
    def _search(self):
        query = self.var_query.get().strip()
        if not query:
            self.lbl_status.config(text="Type a concept first.", foreground="#c0392b")
            return

        # First search loads the model — briefly show a working message.
        self.lbl_status.config(text="Thinking…", foreground="#555")
        self.update_idletasks()

        result = self.service.search(query, top_n=8)

        self.tree.delete(*self.tree.get_children())
        if not result["success"]:
            self.lbl_status.config(text=result["message"], foreground="#c0392b")
            return

        for i, item in enumerate(result["data"]):
            b = item["book"]
            tag = "even" if i % 2 else "odd"
            self.tree.insert(
                "", "end",
                values=(f"{item['score']:.0f}%", b.title, b.author or "", b.category or ""),
                tags=(tag,),
            )
        self.lbl_status.config(text=result["message"], foreground="#555")


# ----------------------------------------------------------------------------
# Standalone preview:  python -m ui.smart_search_view
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Smart Search — Preview")
    root.geometry("820x520")
    view = SmartSearchView(root)
    view.pack(fill="both", expand=True)
    root.mainloop()
