# ============================================================================
# reports/report_generator.py
# ----------------------------------------------------------------------------
# REPORT GENERATOR — exports report data to an Excel file using pandas.
#
# It receives already-prepared data from ReportService (a {columns, rows}
# dict) and writes it to reports/exports/*.xlsx. It does NOT query the
# database — it only turns data into a file.
#
# Main entry point:
#   export_to_excel(report_label, report_data, path=None) -> saved file path
# ============================================================================

import os
import re
from datetime import datetime

import pandas as pd


# Folder where generated files are written (reports/exports/).
EXPORTS_DIR = os.path.join(os.path.dirname(__file__), "exports")


def _safe_filename(label):
    """Turn a report label into a safe file stem, e.g. 'Overdue Books'."""
    stem = re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_") or "report"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stem}_{stamp}.xlsx"


def export_to_excel(report_label, report_data, path=None):
    """
    Write a report to an Excel (.xlsx) file.

    report_label : human name of the report (used for the default filename).
    report_data  : dict {"columns": [(heading, width)...], "rows": [tuple...]}
                   as produced by ReportService.
    path         : optional explicit file path. If omitted, a timestamped file
                   is created under reports/exports/.

    Returns the full path of the saved file.
    Raises ValueError if there is nothing to export.
    """
    columns = report_data.get("columns", [])
    rows = report_data.get("rows", [])

    if not columns:
        raise ValueError("This report has no columns to export.")
    if not rows:
        raise ValueError("This report has no rows to export.")

    headings = [heading for heading, _width in columns]

    # Build a DataFrame with the report's column order preserved.
    frame = pd.DataFrame(rows, columns=headings)

    # Resolve the output path.
    if path is None:
        os.makedirs(EXPORTS_DIR, exist_ok=True)
        path = os.path.join(EXPORTS_DIR, _safe_filename(report_label))

    # Write to Excel (openpyxl engine); sheet name capped at Excel's 31 chars.
    sheet_name = (report_label or "Report")[:31]
    frame.to_excel(path, index=False, sheet_name=sheet_name, engine="openpyxl")
    return path
