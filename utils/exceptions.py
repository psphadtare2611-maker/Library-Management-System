# ============================================================================
# utils/exceptions.py
# ----------------------------------------------------------------------------
# CUSTOM EXCEPTIONS for clear, meaningful error handling.
#
# Will define (to be implemented later) exceptions such as:
#   - BookNotAvailableError    -> tried to issue a book with 0 copies free
#   - BookNotFoundError        -> book id does not exist
#   - BorrowerNotFoundError    -> borrower id does not exist
#   - BookInUseError           -> tried to remove a book that is on loan
#   - ValidationError          -> invalid user input
#
# Services raise these; controllers/UI catch them and show friendly messages.
# This is cleaner than passing error codes or returning None everywhere.
# ============================================================================
