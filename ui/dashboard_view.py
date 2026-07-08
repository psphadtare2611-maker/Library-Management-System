# ============================================================================
# ui/dashboard_view.py
# ----------------------------------------------------------------------------
# DASHBOARD SCREEN — the landing page, shown on startup.
#
# Shows five summary cards (Total Books, Available, Borrowed, Borrowers,
# Today's Transactions) and a row of navigation buttons (Books, Borrowers,
# Issue, Return, Reports, Exit).
#
# Navigation is done via callbacks passed in by the main window (not wired
# here). Each button calls its callback if given; Exit falls back to closing
# the window. The numbers come from ReportService.get_dashboard_stats().
# ============================================================================

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from services.report_service import ReportService
from ui import theme


class DashboardView(tk.Frame):
    """Modern landing screen with stat cards and navigation buttons."""

    # Shared palette (see ui/theme.py).
    BG = theme.BG
    HEADER_BG = theme.HEADER_BG
    HEADER_FG = theme.HEADER_FG

    # (key, title, accent colour) for each card — modern palette.
    CARDS = (
        ("total_books", "Total Books", "#4f46e5"),        # indigo
        ("available_books", "Available Books", "#16a34a"), # green
        ("borrowed_books", "Borrowed Books", "#f59e0b"),   # amber
        ("borrowers", "Borrowers", "#8b5cf6"),             # violet
        ("today_transactions", "Today's Transactions", "#0891b2"),  # cyan
    )

    def __init__(self, parent, report_service=None, callbacks=None):
        """
        callbacks: optional dict mapping button names to functions, e.g.
            {"books": fn, "borrowers": fn, "issue": fn, "return": fn,
             "reports": fn, "exit": fn}
        Any missing entry falls back to a friendly placeholder (Exit closes
        the window).
        """
        super().__init__(parent, bg=self.BG)
        self.report_service = report_service or ReportService()
        self.callbacks = callbacks or {}
        self._value_labels = {}

        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ---- Header --------------------------------------------------------
        header = tk.Frame(self, bg=self.HEADER_BG, height=70)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        tk.Label(
            header, text="  Library Management System",
            bg=self.HEADER_BG, fg=self.HEADER_FG, font=("Segoe UI", 18, "bold"),
        ).place(relx=0.0, rely=0.5, anchor="w", x=18)
        tk.Label(
            header, text=date.today().strftime("%A, %d %B %Y") + "  ",
            bg=self.HEADER_BG, fg="#bdc3c7", font=("Segoe UI", 11),
        ).place(relx=1.0, rely=0.5, anchor="e", x=-10)

        # ---- Cards row -----------------------------------------------------
        cards = tk.Frame(self, bg=self.BG)
        cards.grid(row=1, column=0, sticky="ew", padx=20, pady=(20, 10))
        for i in range(len(self.CARDS)):
            cards.columnconfigure(i, weight=1, uniform="cards")

        for col, (key, title, accent) in enumerate(self.CARDS):
            self._make_card(cards, col, key, title, accent)

        # ---- Navigation buttons -------------------------------------------
        nav_wrap = tk.Frame(self, bg=self.BG)
        nav_wrap.grid(row=2, column=0, sticky="n", pady=(10, 20))

        tk.Label(
            nav_wrap, text="Quick Actions", bg=self.BG, fg="#2c3e50",
            font=("Segoe UI", 13, "bold"),
        ).grid(row=0, column=0, columnspan=6, pady=(0, 12))

        buttons = [
            ("Books", "books", "#4f46e5"),
            ("Borrowers", "borrowers", "#8b5cf6"),
            ("Issue", "issue", "#f59e0b"),
            ("Return", "return", "#0891b2"),
            ("Reports", "reports", "#334155"),
            ("Exit", "exit", "#dc2626"),
        ]
        for col, (label, name, colour) in enumerate(buttons):
            self._make_nav_button(nav_wrap, col, label, name, colour)

        # ---- Status / refresh line ----------------------------------------
        footer = tk.Frame(self, bg=self.BG)
        footer.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 12))
        self.lbl_status = tk.Label(footer, text="", bg=self.BG, fg="#7f8c8d",
                                   font=("Segoe UI", 9))
        self.lbl_status.pack(side="left")
        tk.Button(
            footer, text="⟳ Refresh", command=self.refresh, relief="flat",
            bg="#bdc3c7", fg="#2c3e50", font=("Segoe UI", 9, "bold"),
            padx=10, pady=2, cursor="hand2", activebackground="#95a5a6",
        ).pack(side="right")

    def _make_card(self, parent, col, key, title, accent):
        """Build one stat card with a big number and a caption."""
        card = tk.Frame(parent, bg="#ffffff", highlightbackground="#dfe4e6",
                        highlightthickness=1)
        card.grid(row=0, column=col, sticky="nsew", padx=8, ipady=6)

        # Accent stripe on top.
        tk.Frame(card, bg=accent, height=5).pack(fill="x")

        value = tk.Label(card, text="—", bg="#ffffff", fg=accent,
                         font=("Segoe UI", 30, "bold"))
        value.pack(pady=(14, 2))
        tk.Label(card, text=title, bg="#ffffff", fg="#7f8c8d",
                 font=("Segoe UI", 10)).pack(pady=(0, 14))

        self._value_labels[key] = value

    def _make_nav_button(self, parent, col, label, name, colour):
        """Build one modern navigation tile with a hover effect."""
        btn = tk.Button(
            parent, text=label, width=12, height=2,
            bg=colour, fg="#ffffff", font=("Segoe UI", 11, "bold"),
            relief="flat", cursor="hand2", activebackground=colour,
            activeforeground="#ffffff", bd=0,
            command=lambda n=name: self._navigate(n),
        )
        btn.grid(row=1, column=col, padx=8)

        # Simple hover: darken slightly on enter, restore on leave.
        def on_enter(_e, b=btn, c=colour):
            b.configure(bg=self._darken(c))

        def on_leave(_e, b=btn, c=colour):
            b.configure(bg=c)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

    # ------------------------------------------------------------------ #
    # Data
    # ------------------------------------------------------------------ #
    def refresh(self):
        """Reload the card numbers from the service."""
        result = self.report_service.get_dashboard_stats()
        if result["success"]:
            stats = result["data"]
            for key, label in self._value_labels.items():
                label.config(text=str(stats.get(key, "—")))
            self.lbl_status.config(
                text="Updated " + date.today().strftime("%d %b %Y"), fg="#7f8c8d"
            )
        else:
            for label in self._value_labels.values():
                label.config(text="—")
            self.lbl_status.config(text=result["message"], fg="#c0392b")

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #
    def _navigate(self, name):
        """Call the registered callback, or fall back sensibly."""
        callback = self.callbacks.get(name)
        if callable(callback):
            callback()
            return
        if name == "exit":
            self._exit()
        else:
            messagebox.showinfo(
                name.capitalize(),
                f"'{name.capitalize()}' will open once the main window wires navigation.",
            )

    def _exit(self):
        if messagebox.askokcancel("Exit", "Close the Library Management System?"):
            self.winfo_toplevel().destroy()

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _darken(hex_colour, factor=0.85):
        """Return a slightly darker shade of a #rrggbb colour (for hover)."""
        hex_colour = hex_colour.lstrip("#")
        r, g, b = (int(hex_colour[i:i + 2], 16) for i in (0, 2, 4))
        r, g, b = (int(c * factor) for c in (r, g, b))
        return f"#{r:02x}{g:02x}{b:02x}"


# ----------------------------------------------------------------------------
# Standalone preview:  python -m ui.dashboard_view
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Dashboard — Preview")
    root.geometry("980x560")
    view = DashboardView(root)
    view.pack(fill="both", expand=True)
    root.mainloop()
