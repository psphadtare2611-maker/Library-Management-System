# ============================================================================
# database/borrower_repository.py
# ----------------------------------------------------------------------------
# BORROWER REPOSITORY — all SQL for the Borrowers table (Data Access Layer).
#
# Responsibilities (to be implemented later):
#   - add_borrower()         -> INSERT a new borrower (friend)
#   - update_borrower()      -> UPDATE borrower details
#   - deactivate_borrower()  -> soft-delete via is_active = 0
#   - get_borrower_by_id()   -> fetch a single borrower
#   - get_all_borrowers()    -> fetch all borrowers
#   - search_borrowers()     -> find by name / phone / email
#
# Contains SQL ONLY. No business rules here — those live in services/.
# ============================================================================
