# ============================================================================
# services/report_service.py
# ----------------------------------------------------------------------------
# REPORT SERVICE — builds the data behind the Reports screen.
#
# Responsibilities (to be implemented later):
#   - currently_borrowed()   -> all books currently out (with borrower + due date)
#   - overdue_report()       -> active loans past due
#   - most_borrowed_books()  -> ranking by number of times issued
#   - borrower_summary()     -> per-friend borrowing counts / history
#
# Reads aggregated data via the repositories and hands it to reports/ for
# formatting/exporting. Contains reporting rules, not raw SQL.
# ============================================================================
