# ============================================================================
# models/transaction.py
# ----------------------------------------------------------------------------
# TRANSACTION ENTITY — a plain data class representing one borrowing record.
#
# Will hold (to be implemented later) attributes such as:
#   transaction_id, book_id, borrower_id,
#   issue_date, due_date, return_date, status, fine_amount
#
# This is the core record of the system: one row per issue event.
# return_date == None means the book is still out.
# Contains data only, no SQL and no business rules.
# ============================================================================
