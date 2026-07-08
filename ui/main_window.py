# ============================================================================
# ui/main_window.py
# ----------------------------------------------------------------------------
# MAIN APPLICATION WINDOW — the root Tkinter window and navigation shell.
#
# Layout:
#   +----------+--------------------------------------------+
#   | sidebar  |  content area (the active screen)          |
#   |  (nav)   |                                            |
#   +----------+--------------------------------------------+
#
# The sidebar routes to each screen; the content area swaps in a freshly
# built view each time (so every screen shows current data). The Dashboard's
# own buttons are wired to the same navigation via callbacks.
#
# This shell owns NO business logic — it only creates views (which talk to the
# service layer themselves) and switches between them.
# ============================================================================

import tkinter as tk
from tkinter import messagebox

from config.settings import APP_NAME
from utils.logger import logger
from ui import theme

from ui.dashboard_view import DashboardView
from ui.book_view import BookListView
from ui.add_book_view import AddBookView
from ui.borrower_view import BorrowerListView
from ui.circulation_view import IssueBookView, ReturnBookView
from ui.report_view import ReportView
from ui.statistics_view import StatisticsView
from ui.search_view import UniversalSearchView
from ui.recommendation_view import RecommendationView
from ui.smart_search_view import SmartSearchView


class MainWindow(tk.Tk):
    """Root window: a sidebar of screens plus a swappable content area."""

    SIDEBAR_BG = "#1f2d3d"      # slightly darker than the header bars
    SIDEBAR_ACTIVE = theme.ACCENT
    SIDEBAR_FG = "#ecf0f1"

    # (label, key) pairs, in the order they appear in the sidebar.
    NAV_ITEMS = (
        ("🏠  Dashboard", "dashboard"),
        ("📚  Books", "books"),
        ("➕  Add Book", "add_book"),
        ("👥  Borrowers", "borrowers"),
        ("📤  Issue Book", "issue"),
        ("📥  Return Book", "return"),
        ("📊  Reports", "reports"),
        ("📈  Statistics", "statistics"),
        ("🔍  Search", "search"),
        ("🧠  Smart Search", "smart_search"),
        ("🤝  Recommend", "recommend"),
    )

    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1150x700")
        self.minsize(950, 620)

        self._content = None        # the currently displayed view
        self._nav_buttons = {}      # key -> sidebar button (for highlighting)
        self._active_key = None

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        logger.info("Application started")
        self.show("dashboard")

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ---- Sidebar -------------------------------------------------------
        sidebar = tk.Frame(self, bg=self.SIDEBAR_BG, width=210)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)

        tk.Label(
            sidebar, text="📖  Library", bg=self.SIDEBAR_BG, fg="#ffffff",
            font=("Segoe UI", 15, "bold"), pady=18,
        ).pack(fill="x")

        for label, key in self.NAV_ITEMS:
            self._make_nav_button(sidebar, label, key)

        # Exit pinned to the bottom.
        tk.Button(
            sidebar, text="🚪  Exit", command=self._on_exit,
            bg=self.SIDEBAR_BG, fg="#e74c3c", font=("Segoe UI", 11, "bold"),
            relief="flat", anchor="w", padx=20, pady=10, bd=0,
            activebackground="#c0392b", activeforeground="#ffffff", cursor="hand2",
        ).pack(side="bottom", fill="x")

        # ---- Content area --------------------------------------------------
        self._content_area = tk.Frame(self, bg="#ffffff")
        self._content_area.grid(row=0, column=1, sticky="nsew")
        self._content_area.rowconfigure(0, weight=1)
        self._content_area.columnconfigure(0, weight=1)

    def _make_nav_button(self, parent, label, key):
        """Create one sidebar navigation button with a hover effect."""
        btn = tk.Button(
            parent, text=label, command=lambda k=key: self.show(k),
            bg=self.SIDEBAR_BG, fg=self.SIDEBAR_FG, font=("Segoe UI", 11),
            relief="flat", anchor="w", padx=20, pady=10, bd=0,
            activebackground=self.SIDEBAR_ACTIVE, activeforeground="#ffffff",
            cursor="hand2",
        )
        btn.pack(fill="x")

        # Hover only affects inactive buttons (the active one keeps its colour).
        def on_enter(_e, b=btn, k=key):
            if k != self._active_key:
                b.configure(bg="#2a3b4d")

        def on_leave(_e, b=btn, k=key):
            if k != self._active_key:
                b.configure(bg=self.SIDEBAR_BG)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        self._nav_buttons[key] = btn

    # ------------------------------------------------------------------ #
    # Navigation
    # ------------------------------------------------------------------ #
    def show(self, key):
        """Swap the content area to the screen identified by `key`."""
        # Tear down the previous view.
        if self._content is not None:
            self._content.destroy()
            self._content = None

        try:
            self._content = self._build_view(key)
            self._content.grid(row=0, column=0, sticky="nsew")
        except Exception as error:
            # A screen should never take the whole app down.
            logger.error(f"Failed to open screen '{key}': {error}")
            messagebox.showerror("Error", f"Could not open the '{key}' screen.")
            return

        self._highlight(key)

    def _build_view(self, key):
        """Create a fresh view for `key`, parented to the content area."""
        parent = self._content_area
        if key == "dashboard":
            return DashboardView(parent, callbacks=self._dashboard_callbacks())
        if key == "books":
            return BookListView(parent)
        if key == "add_book":
            # Back returns to the book list.
            return AddBookView(parent, on_back=lambda: self.show("books"))
        if key == "borrowers":
            return BorrowerListView(parent)
        if key == "issue":
            return IssueBookView(parent)
        if key == "return":
            return ReturnBookView(parent)
        if key == "reports":
            return ReportView(parent)
        if key == "statistics":
            return StatisticsView(parent)
        if key == "search":
            return UniversalSearchView(parent)
        if key == "smart_search":
            return SmartSearchView(parent)
        if key == "recommend":
            return RecommendationView(parent)
        raise ValueError(f"Unknown screen '{key}'")

    def _dashboard_callbacks(self):
        """Wire the Dashboard's own buttons to the sidebar navigation."""
        return {
            "books": lambda: self.show("books"),
            "borrowers": lambda: self.show("borrowers"),
            "issue": lambda: self.show("issue"),
            "return": lambda: self.show("return"),
            "reports": lambda: self.show("reports"),
            "exit": self._on_exit,
        }

    def _highlight(self, key):
        """Mark the active sidebar button and reset the others."""
        self._active_key = key
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(bg=self.SIDEBAR_ACTIVE, fg="#ffffff")
            else:
                btn.configure(bg=self.SIDEBAR_BG, fg=self.SIDEBAR_FG)

    # ------------------------------------------------------------------ #
    # Shutdown
    # ------------------------------------------------------------------ #
    def _on_exit(self):
        if messagebox.askokcancel("Exit", "Close the Library Management System?"):
            self._shutdown()

    def _on_close(self):
        # The window's X button: close without an extra confirmation.
        self._shutdown()

    def _shutdown(self):
        logger.info("Application closed")
        self.destroy()
