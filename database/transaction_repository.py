# ============================================================================
# database/transaction_repository.py
# ----------------------------------------------------------------------------
# TRANSACTION REPOSITORY — all SQL for the Transactions table.
# This is the most important repository: it records every issue/return event.
#
# Responsibilities (to be implemented later):
#   - create_transaction()      -> INSERT on book issue
#   - mark_returned()           -> UPDATE return_date + status on return
#   - get_active_loans()        -> rows WHERE return_date IS NULL (books out now)
#   - get_overdue_loans()       -> active loans past their due_date
#   - get_history()             -> full borrowing log, with filters
#   - get_history_by_borrower() -> everything a given friend has borrowed
#   - get_history_by_book()     -> everyone who borrowed a given book
#
# Contains SQL ONLY. No business rules here — those live in services/.
# ============================================================================
