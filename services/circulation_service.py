# ============================================================================
# services/circulation_service.py
# ----------------------------------------------------------------------------
# CIRCULATION SERVICE — the heart of the application: issuing & returning.
#
# Responsibilities (to be implemented later):
#   ISSUE a book:
#     - check the book exists and available_copies > 0
#     - check the borrower exists and is active
#     - calculate due_date (issue_date + LOAN_PERIOD_DAYS from settings)
#     - create a Transaction and decrement available_copies
#
#   RETURN a book:
#     - locate the active transaction
#     - set return_date, update status, increment available_copies
#     - compute overdue days / fine if applicable
#
# This is where the most important business rules live. It coordinates the
# book_repository and transaction_repository together for each operation.
# ============================================================================
