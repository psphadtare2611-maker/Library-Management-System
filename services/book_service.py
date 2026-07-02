# ============================================================================
# services/book_service.py
# ----------------------------------------------------------------------------
# BOOK SERVICE — business logic for managing books.
#
# Responsibilities (to be implemented later):
#   - add_book()     -> validate input, then call book_repository
#   - update_book()  -> validate, then persist changes
#   - remove_book()  -> guard rule: refuse to remove a book that is currently
#                       issued; otherwise soft-delete it
#   - search_books() -> pass query to the repository
#
# Calls the repository for data; applies validation and rules on top.
# The UI talks to this class, never directly to the database.
# ============================================================================
