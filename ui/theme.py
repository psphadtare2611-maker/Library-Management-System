# ============================================================================
# ui/theme.py
# ----------------------------------------------------------------------------
# UI THEME & DESIGN SYSTEM — one place for the app's colours, fonts, and the
# global ttk widget styling.
#
# apply_global_style() is called ONCE at startup (from the main window) and
# restyles every standard widget — buttons, entries, comboboxes, tables,
# scrollbars — so the whole app shares one modern look. Individual screens just
# reference the palette constants below (theme.HEADER_BG, theme.ACCENT, ...).
#
# Palette: a modern "slate + indigo" scheme (dark slate chrome, indigo accent,
# soft slate-grey page background, white cards).
# ============================================================================

import tkinter as tk
from tkinter import ttk


# --- Brand / accent ---------------------------------------------------------
PRIMARY = "#4f46e5"        # indigo — primary actions
PRIMARY_DARK = "#4338ca"   # hover/pressed
ACCENT = "#4f46e5"         # alias used by older code (selection colour, etc.)

# --- Chrome (sidebar + headers) --------------------------------------------
SIDEBAR_BG = "#0f172a"     # near-black slate
SIDEBAR_HOVER = "#1e293b"
SIDEBAR_ACTIVE = "#4f46e5"
SIDEBAR_FG = "#cbd5e1"
HEADER_BG = "#1e293b"      # screen header bars
HEADER_FG = "#ffffff"

# --- Surfaces ---------------------------------------------------------------
BG = "#f1f5f9"             # page background (slate-100)
CARD_BG = "#ffffff"        # cards / tables
BORDER = "#e2e8f0"         # hairline borders

# --- Table rows -------------------------------------------------------------
ROW_ODD = "#ffffff"
ROW_EVEN = "#f8fafc"

# --- Text -------------------------------------------------------------------
TEXT = "#0f172a"           # primary text (slate-900)
MUTED = "#64748b"          # secondary text (slate-500)

# --- Semantic ---------------------------------------------------------------
SUCCESS = "#16a34a"        # green
ERROR = "#dc2626"          # red
WARNING = "#d97706"        # amber

# --- Typography -------------------------------------------------------------
FONT_FAMILY = "Segoe UI"
FONT = (FONT_FAMILY, 10)
FONT_BOLD = (FONT_FAMILY, 10, "bold")
FONT_H1 = (FONT_FAMILY, 17, "bold")


def apply_global_style():
    """Configure the ttk styling for the whole application (call once)."""
    style = ttk.Style()
    try:
        style.theme_use("clam")   # 'clam' is the most controllable built-in theme
    except tk.TclError:
        pass

    # ---- Base ----------------------------------------------------------
    style.configure(".", font=FONT, background=BG, foreground=TEXT)
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure("TLabelframe", background=BG, bordercolor=BORDER)
    style.configure("TLabelframe.Label", background=BG, foreground=MUTED)

    # ---- Buttons (flat, padded, subtle hover) --------------------------
    style.configure("TButton", background="#e2e8f0", foreground=TEXT,
                    borderwidth=0, focuscolor=BG, padding=(14, 8), font=FONT_BOLD)
    style.map("TButton",
              background=[("pressed", "#94a3b8"), ("active", "#cbd5e1")])

    # Primary (accent) button — for the main action on a screen.
    style.configure("Primary.TButton", background=PRIMARY, foreground="#ffffff",
                    borderwidth=0, padding=(16, 8), font=FONT_BOLD)
    style.map("Primary.TButton",
              background=[("pressed", "#3730a3"), ("active", PRIMARY_DARK)])

    # Danger button — destructive actions.
    style.configure("Danger.TButton", background=ERROR, foreground="#ffffff",
                    borderwidth=0, padding=(14, 8), font=FONT_BOLD)
    style.map("Danger.TButton",
              background=[("pressed", "#991b1b"), ("active", "#b91c1c")])

    # ---- Inputs --------------------------------------------------------
    style.configure("TEntry", fieldbackground="#ffffff", foreground=TEXT,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                    borderwidth=1, padding=6, relief="solid")
    style.map("TEntry", bordercolor=[("focus", PRIMARY)],
              lightcolor=[("focus", PRIMARY)], darkcolor=[("focus", PRIMARY)])

    style.configure("TCombobox", fieldbackground="#ffffff", background="#ffffff",
                    foreground=TEXT, bordercolor=BORDER, arrowcolor=TEXT,
                    borderwidth=1, padding=6, relief="solid")
    style.map("TCombobox",
              fieldbackground=[("readonly", "#ffffff")],
              bordercolor=[("focus", PRIMARY)])

    # ---- Scrollbars (slim, flat) ---------------------------------------
    for orient in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        style.configure(orient, background="#cbd5e1", troughcolor=BG,
                        borderwidth=0, arrowcolor=TEXT)
        style.map(orient, background=[("active", "#94a3b8")])

    _configure_treeview(style)


def apply_treeview_style(rowheight=30):
    """Apply the shared table styling (also re-callable per screen)."""
    _configure_treeview(ttk.Style(), rowheight)


def _configure_treeview(style, rowheight=30):
    style.configure(
        "Treeview", rowheight=rowheight, font=FONT,
        background=CARD_BG, fieldbackground=CARD_BG, foreground=TEXT,
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading", font=(FONT_FAMILY, 10, "bold"),
        background=HEADER_BG, foreground="#ffffff", padding=8,
        borderwidth=0, relief="flat",
    )
    style.map("Treeview.Heading", background=[("active", "#334155")])
    style.map("Treeview",
              background=[("selected", PRIMARY)],
              foreground=[("selected", "#ffffff")])
