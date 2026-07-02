# ============================================================================
# utils/date_helper.py
# ----------------------------------------------------------------------------
# DATE / TIME helpers for borrowing logic.
#
# Will provide (to be implemented later):
#   - calculate_due_date()  -> issue_date + LOAN_PERIOD_DAYS
#   - days_overdue()        -> how many days past due a loan is (0 if not)
#   - is_overdue()          -> True if due_date has passed and not returned
#   - format_date()         -> consistent date display for the UI
#
# Centralizing date math keeps the overdue rules correct and in one place.
# ============================================================================
