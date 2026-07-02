# ============================================================================
# ui/theme.py
# ----------------------------------------------------------------------------
# UI THEME — one place for the shared colour palette and the common ttk
# Treeview styling.
#
# Before this module, every screen hard-coded the same hex colours and copied
# the same ~10 lines of Treeview styling. Centralizing them here removes that
# duplication (DRY): change a colour once and every screen updates.
# ============================================================================

import tkinter as tk
from tkinter import ttk


# --- Core palette -----------------------------------------------------------
HEADER_BG = "#2c3e50"   # dark header bar background
HEADER_FG = "#ffffff"   # header text
BG = "#ecf0f1"          # neutral page background (dashboards)

# --- Table row striping -----------------------------------------------------
ROW_ODD = "#ffffff"
ROW_EVEN = "#f4f6f7"

# --- Selection / accent -----------------------------------------------------
ACCENT = "#2980b9"      # selected row / primary accent

# --- Semantic text colours --------------------------------------------------
SUCCESS = "#27ae60"     # green — success messages
ERROR = "#c0392b"       # red — error messages
MUTED = "#7f8c8d"       # grey — secondary/status text


def apply_treeview_style(rowheight=26):
    """
    Apply the shared, professional Treeview look (theme, row height, fonts,
    bold dark headings, blue selection).

    rowheight : per-row pixel height (a couple of screens use a slightly
                tighter row, so it is adjustable while everything else stays
                identical).
    """
    style = ttk.Style()
    try:
        style.theme_use("clam")   # 'clam' gives clean, controllable styling
    except tk.TclError:
        pass
    style.configure(
        "Treeview", rowheight=rowheight, font=("Segoe UI", 10),
        background="#ffffff", fieldbackground="#ffffff",
    )
    style.configure(
        "Treeview.Heading", font=("Segoe UI", 10, "bold"),
        background=HEADER_BG, foreground="#ffffff", padding=6,
    )
    style.map(
        "Treeview",
        background=[("selected", ACCENT)],
        foreground=[("selected", "#ffffff")],
    )
