# ============================================================================
# services/borrower_service.py
# ----------------------------------------------------------------------------
# BORROWER SERVICE — business logic for managing borrowers (friends).
#
# Responsibilities (to be implemented later):
#   - add_borrower()        -> validate (name required, valid phone/email)
#   - update_borrower()     -> validate and persist
#   - remove_borrower()     -> guard rule: refuse if the borrower currently
#                              holds a book; otherwise deactivate
#   - search_borrowers()    -> pass query to the repository
#
# Applies validation and rules; delegates data access to borrower_repository.
# ============================================================================
