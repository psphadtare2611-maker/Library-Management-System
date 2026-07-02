# ============================================================================
# ui/report_view.py
# ----------------------------------------------------------------------------
# REPORTS SCREEN — pick a report, view it in a Treeview, export to Excel.
#
# Reports:
#   - Available Books
#   - Borrowed Books
#   - Overdue Books
#   - Borrow History
#   - Most Borrowed Books
#
# The Treeview is rebuilt for whichever report is chosen (each report has its
# own columns). Export to Excel hands the currently displayed report to
# reports.report_generator (pandas).
#
# Presentation only: data comes from ReportService; export from report_generator.
# ============================================================================

import os
import tkinter as tk
from tkinter import ttk, messagebox

from services.report_service import ReportService
from reports.report_generator import export_to_excel
from ui import theme


class ReportView(ttk.Frame):
    """Report chooser + Treeview display + Excel export."""

    # Shared palette (see ui/theme.py).
    HEADER_BG = theme.HEADER_BG
    HEADER_FG = theme.HEADER_FG
    ROW_ODD = theme.ROW_ODD
    ROW_EVEN = theme.ROW_EVEN

    def __init__(self, parent, report_service=None):
        super().__init__(parent, padding=0)
        self.report_service = report_service or ReportService()

        # Map each menu label to the service method that builds it.
        self._reports = {
            "Available Books": self.report_service.available_books,
            "Borrowed Books": self.report_service.borrowed_books,
            "Overdue Books": self.report_service.overdue_books,
            "Borrow History": self.report_service.borrow_history,
            "Most Borrowed Books": self.report_service.most_borrowed_books,
        }

        # Holds the currently displayed report for export.
        self._current_label = None
        self._current_data = None

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
            header, text="  Reports", bg=self.HEADER_BG, fg=self.HEADER_FG,
            font=("Segoe UI", 16, "bold"),
        ).place(relx=0.0, rely=0.5, anchor="w", x=15)

        # ---- Toolbar (choose report + actions) ----------------------------
        toolbar = ttk.Frame(self, padding=(15, 12))
        toolbar.grid(row=1, column=0, sticky="ew")

        ttk.Label(toolbar, text="Report:").pack(side="left", padx=(0, 6))
        self.cmb_report = ttk.Combobox(
            toolbar, state="readonly", width=26, values=list(self._reports.keys())
        )
        self.cmb_report.pack(side="left")
        self.cmb_report.bind("<<ComboboxSelected>>", lambda e: self._generate())

        ttk.Button(toolbar, text="Generate", command=self._generate).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Export to Excel", command=self._export).pack(side="left")

        # ---- Treeview (rebuilt per report) --------------------------------
        self._apply_style()
        self.table_wrap = ttk.Frame(self, padding=(15, 0, 15, 10))
        self.table_wrap.grid(row=2, column=0, sticky="nsew")
        self.table_wrap.rowconfigure(0, weight=1)
        self.table_wrap.columnconfigure(0, weight=1)
        self.tree = None  # created on first report

        # ---- Status line ---------------------------------------------------
        self.lbl_status = ttk.Label(self, text="Choose a report to begin.",
                                    padding=(15, 4), foreground="#555")
        self.lbl_status.grid(row=3, column=0, sticky="w")

    def _apply_style(self):
        """Apply the shared professional Treeview styling (see ui/theme.py)."""
        theme.apply_treeview_style()

    # ------------------------------------------------------------------ #
    # Generate / display a report
    # ------------------------------------------------------------------ #
    def _generate(self):
        label = self.cmb_report.get()
        if not label:
            self._set_status("Please choose a report first.", error=True)
            return

        result = self._reports[label]()
        if not result["success"]:
            self._set_status(result["message"], error=True)
            return

        self._current_label = label
        self._current_data = result["data"]
        self._render(result["data"])
        self._set_status(f"{label} — {result['message']}")

    def _render(self, data):
        """Rebuild the Treeview for this report's columns and rows."""
        # Remove any previous tree.
        if self.tree is not None:
            self.tree.destroy()

        columns = data["columns"]           # list of (heading, width)
        col_ids = [f"c{i}" for i in range(len(columns))]

        self.tree = ttk.Treeview(self.table_wrap, columns=col_ids,
                                 show="headings", selectmode="browse")
        for col_id, (heading, width) in zip(col_ids, columns):
            self.tree.heading(col_id, text=heading)
            self.tree.column(col_id, width=width, stretch=True, anchor="w")

        vsb = ttk.Scrollbar(self.table_wrap, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.table_wrap, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.tag_configure("odd", background=self.ROW_ODD)
        self.tree.tag_configure("even", background=self.ROW_EVEN)

        for index, row in enumerate(data["rows"]):
            # Show blanks instead of 'None' for empty cells (e.g. return date).
            values = ["" if v is None else v for v in row]
            tag = "even" if index % 2 else "odd"
            self.tree.insert("", "end", values=values, tags=(tag,))

    # ------------------------------------------------------------------ #
    # Export
    # ------------------------------------------------------------------ #
    def _export(self):
        if not self._current_data:
            self._set_status("Generate a report before exporting.", error=True)
            return
        try:
            path = export_to_excel(self._current_label, self._current_data)
        except ValueError as empty_error:
            # e.g. no rows to export.
            self._set_status(str(empty_error), error=True)
            messagebox.showwarning("Nothing to export", str(empty_error))
            return
        except Exception as error:
            self._set_status(f"Export failed: {error}", error=True)
            messagebox.showerror("Export failed", str(error))
            return

        self._set_status(f"Exported to {path}")
        messagebox.showinfo("Exported", f"Saved to:\n{os.path.abspath(path)}")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _set_status(self, message, error=False):
        self.lbl_status.config(text=message, foreground="#c0392b" if error else "#555")


# ----------------------------------------------------------------------------
# Standalone preview:  python -m ui.report_view
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Reports — Preview")
    root.geometry("880x560")
    view = ReportView(root)
    view.pack(fill="both", expand=True)
    root.mainloop()
