# ============================================================================
# ui/recommendation_view.py
# ----------------------------------------------------------------------------
# RECOMMENDATIONS SCREEN — "You might also like…"
#
# Pick a book; the screen shows the most similar books, ranked by a match
# percentage, using RecommendationService (content-based ML: TF-IDF + cosine
# similarity). Presentation only — all the ML lives in the service.
# ============================================================================

import tkinter as tk
from tkinter import ttk

from services.book_service import BookService
from services.recommendation_service import RecommendationService
from ui import theme


class RecommendationView(ttk.Frame):
    """Choose a book and see content-based recommendations."""

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

    def __init__(self, parent, book_service=None, recommendation_service=None):
        super().__init__(parent, padding=0)
        self.book_service = book_service or BookService()
        self.recommender = recommendation_service or RecommendationService(self.book_service)
        self._books = []            # parallel list for the dropdown
        self._build_ui()
        self._load_books()

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
            header, text="  You Might Also Like…", bg=self.HEADER_BG, fg=self.HEADER_FG,
            font=("Segoe UI", 16, "bold"),
        ).place(relx=0.0, rely=0.5, anchor="w", x=15)

        # Chooser row
        bar = ttk.Frame(self, padding=(15, 14))
        bar.grid(row=1, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)
        ttk.Label(bar, text="Pick a book:").grid(row=0, column=0, padx=(0, 8))
        self.cmb_book = ttk.Combobox(bar, state="readonly", font=("Segoe UI", 10))
        self.cmb_book.grid(row=0, column=1, sticky="ew")
        self.cmb_book.bind("<<ComboboxSelected>>", lambda e: self._recommend())
        ttk.Button(bar, text="Recommend", command=self._recommend).grid(row=0, column=2, padx=(8, 0))

        ttk.Label(
            self, text="Suggestions are based on title, author and category "
                       "(content-based similarity).",
            foreground="#888", padding=(16, 0),
        ).grid(row=2, column=0, sticky="w")

        # Results table
        wrap = ttk.Frame(self, padding=(15, 8, 15, 10))
        wrap.grid(row=3, column=0, sticky="nsew")
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)

        theme.apply_treeview_style()
        col_ids = [c[0] for c in self.COLUMNS]
        self.tree = ttk.Treeview(wrap, columns=col_ids, show="headings", selectmode="browse")
        for col_id, heading, width, stretch in self.COLUMNS:
            self.tree.heading(col_id, text=heading)
            anchor = "center" if col_id == "match" else "w"
            self.tree.column(col_id, width=width, stretch=stretch, anchor=anchor)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.tag_configure("odd", background=self.ROW_ODD)
        self.tree.tag_configure("even", background=self.ROW_EVEN)

        self.lbl_status = ttk.Label(self, text="", padding=(15, 4), foreground="#555")
        self.lbl_status.grid(row=4, column=0, sticky="w")

    # ------------------------------------------------------------------ #
    # Data
    # ------------------------------------------------------------------ #
    def _load_books(self):
        result = self.book_service.get_all_books()
        self._books = result["data"] or [] if result["success"] else []
        self.cmb_book["values"] = [
            f"{b.title}" + (f" — {b.author}" if b.author else "") for b in self._books
        ]
        if not self._books:
            self.lbl_status.config(text="No books in the library yet.", foreground="#c0392b")

    def _recommend(self):
        index = self.cmb_book.current()
        if index < 0:
            self.lbl_status.config(text="Please pick a book first.", foreground="#c0392b")
            return
        book = self._books[index]
        result = self.recommender.recommend(book.book_id, top_n=5)

        self.tree.delete(*self.tree.get_children())
        if not result["success"]:
            self.lbl_status.config(text=result["message"], foreground="#c0392b")
            return

        for i, item in enumerate(result["data"]):
            bk = item["book"]
            tag = "even" if i % 2 else "odd"
            self.tree.insert(
                "", "end",
                values=(f"{item['score']:.0f}%", bk.title, bk.author or "", bk.category or ""),
                tags=(tag,),
            )
        self.lbl_status.config(
            text=f"Because you picked “{book.title}” — {result['message']}",
            foreground="#555",
        )


# ----------------------------------------------------------------------------
# Standalone preview:  python -m ui.recommendation_view
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Recommendations — Preview")
    root.geometry("820x520")
    view = RecommendationView(root)
    view.pack(fill="both", expand=True)
    root.mainloop()
