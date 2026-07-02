# ============================================================================
# database/book_repository.py
# ----------------------------------------------------------------------------
# BOOK REPOSITORY — all SQL for the Books table (Data Access Layer).
#
# Responsibilities (to be implemented later):
#   - add_book()          -> INSERT a new book
#   - update_book()       -> UPDATE book details
#   - soft_delete_book()  -> mark is_active = 0 (never hard-delete: keep history)
#   - get_book_by_id()    -> fetch a single book
#   - get_all_books()     -> fetch the catalog
#   - search_books()      -> SELECT ... LIKE by title / author / category
#
# Contains SQL ONLY. No business rules here — those live in services/.
# ============================================================================
