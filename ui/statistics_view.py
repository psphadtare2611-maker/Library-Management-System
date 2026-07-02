# ============================================================================
# ui/statistics_view.py
# ----------------------------------------------------------------------------
# STATISTICS SCREEN — shows the aggregate numbers from StatisticsService.
#
#   - Four summary cards: Total Books, Borrowed, Available, Total Borrowers
#   - Two highlights: Most Borrowed Author, Most Borrowed Category
#   - A table: Books Borrowed per Person
#
# Presentation only: every number is computed in SQL by StatisticsService.
# ============================================================================

import tkinter as tk
from tkinter import ttk

from services.statistics_service import StatisticsService


class StatisticsView(tk.Frame):
    """Analytics screen driven by StatisticsService."""

    BG = "#ecf0f1"
    HEADER_BG = "#2c3e50"
    HEADER_FG = "#ffffff"

    CARDS = (
        ("total_books", "Total Books", "#3498db"),
        ("borrowed_books", "Borrowed Books", "#e67e22"),
        ("available_books", "Available Books", "#27ae60"),
        ("total_borrowers", "Total Borrowers", "#8e44ad"),
    )

    def __init__(self, parent, service=None):
        super().__init__(parent, bg=self.BG)
        self.service = service or StatisticsService()
        self._value_labels = {}
        self._build_ui()
        self.refresh()

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
        tk.Label(header, text="  Statistics", bg=self.HEADER_BG, fg=self.HEADER_FG,
                 font=("Segoe UI", 16, "bold")).place(relx=0.0, rely=0.5, anchor="w", x=15)
        tk.Button(header, text="⟳ Refresh", command=self.refresh, relief="flat",
                  bg="#34495e", fg="#ffffff", font=("Segoe UI", 9, "bold"),
                  padx=10, cursor="hand2", activebackground="#456").place(
                      relx=1.0, rely=0.5, anchor="e", x=-12)

        # ---- Summary cards -------------------------------------------------
        cards = tk.Frame(self, bg=self.BG)
        cards.grid(row=1, column=0, sticky="ew", padx=20, pady=(18, 8))
        for i in range(len(self.CARDS)):
            cards.columnconfigure(i, weight=1, uniform="c")
        for col, (key, title, accent) in enumerate(self.CARDS):
            self._make_card(cards, col, key, title, accent)

        # ---- Highlights (top author / category) ---------------------------
        highs = tk.Frame(self, bg=self.BG)
        highs.grid(row=2, column=0, sticky="ew", padx=20, pady=(4, 8))
        highs.columnconfigure(0, weight=1)
        highs.columnconfigure(1, weight=1)
        self.lbl_author = self._make_highlight(highs, 0, "Most Borrowed Author", "#c0392b")
        self.lbl_category = self._make_highlight(highs, 1, "Most Borrowed Category", "#16a085")

        # ---- Per-person table ---------------------------------------------
        table_card = tk.Frame(self, bg="#ffffff", highlightbackground="#dfe4e6",
                              highlightthickness=1)
        table_card.grid(row=3, column=0, sticky="nsew", padx=20, pady=(4, 16))
        table_card.rowconfigure(1, weight=1)
        table_card.columnconfigure(0, weight=1)

        tk.Label(table_card, text="Books Borrowed per Person", bg="#ffffff",
                 fg="#2c3e50", font=("Segoe UI", 12, "bold")).grid(
                     row=0, column=0, sticky="w", padx=12, pady=10)

        self._apply_style()
        self.tree = ttk.Treeview(table_card, columns=("name", "count"),
                                 show="headings", selectmode="browse")
        self.tree.heading("name", text="Borrower")
        self.tree.heading("count", text="Books Borrowed")
        self.tree.column("name", width=280, stretch=True, anchor="w")
        self.tree.column("count", width=140, stretch=False, anchor="center")
        vsb = ttk.Scrollbar(table_card, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=1, column=0, sticky="nsew", padx=(12, 0), pady=(0, 12))
        vsb.grid(row=1, column=1, sticky="ns", pady=(0, 12), padx=(0, 12))
        self.tree.tag_configure("odd", background="#ffffff")
        self.tree.tag_configure("even", background="#f4f6f7")

        # ---- Status --------------------------------------------------------
        self.lbl_status = tk.Label(self, text="", bg=self.BG, fg="#7f8c8d",
                                   font=("Segoe UI", 9))
        self.lbl_status.grid(row=4, column=0, sticky="w", padx=22, pady=(0, 8))

    def _make_card(self, parent, col, key, title, accent):
        card = tk.Frame(parent, bg="#ffffff", highlightbackground="#dfe4e6",
                        highlightthickness=1)
        card.grid(row=0, column=col, sticky="nsew", padx=8, ipady=6)
        tk.Frame(card, bg=accent, height=5).pack(fill="x")
        value = tk.Label(card, text="—", bg="#ffffff", fg=accent,
                         font=("Segoe UI", 28, "bold"))
        value.pack(pady=(12, 2))
        tk.Label(card, text=title, bg="#ffffff", fg="#7f8c8d",
                 font=("Segoe UI", 10)).pack(pady=(0, 12))
        self._value_labels[key] = value

    def _make_highlight(self, parent, col, title, accent):
        box = tk.Frame(parent, bg="#ffffff", highlightbackground="#dfe4e6",
                       highlightthickness=1)
        box.grid(row=0, column=col, sticky="ew", padx=8, ipady=10)
        tk.Label(box, text=title, bg="#ffffff", fg="#7f8c8d",
                 font=("Segoe UI", 10)).pack(pady=(8, 2))
        value = tk.Label(box, text="—", bg="#ffffff", fg=accent,
                         font=("Segoe UI", 15, "bold"))
        value.pack(pady=(0, 8))
        return value

    def _apply_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=25, font=("Segoe UI", 10),
                        background="#ffffff", fieldbackground="#ffffff")
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"),
                        background=self.HEADER_BG, foreground="#ffffff", padding=6)

    # ------------------------------------------------------------------ #
    # Data
    # ------------------------------------------------------------------ #
    def refresh(self):
        result = self.service.get_statistics()
        if not result["success"]:
            for label in self._value_labels.values():
                label.config(text="—")
            self.lbl_status.config(text=result["message"], fg="#c0392b")
            return

        data = result["data"]
        for key, label in self._value_labels.items():
            label.config(text=str(data.get(key, "—")))

        author = data["top_author"]
        self.lbl_author.config(
            text=f"{author['author']}  ({author['count']})" if author else "No data yet")
        category = data["top_category"]
        self.lbl_category.config(
            text=f"{category['category']}  ({category['count']})" if category else "No data yet")

        self.tree.delete(*self.tree.get_children())
        for index, person in enumerate(data["per_person"]):
            tag = "even" if index % 2 else "odd"
            self.tree.insert("", "end", values=(person["name"], person["count"]), tags=(tag,))

        self.lbl_status.config(text=result["message"], fg="#7f8c8d")


# ----------------------------------------------------------------------------
# Standalone preview:  python -m ui.statistics_view
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Statistics — Preview")
    root.geometry("900x600")
    view = StatisticsView(root)
    view.pack(fill="both", expand=True)
    root.mainloop()
