# ============================================================================
# services/search_service.py
# ----------------------------------------------------------------------------
# SEARCH SERVICE — one universal search across the whole library.
#
# A single keyword is matched against:
#   Books      -> Title, Author, Category, Status
#   Borrowers  -> Name, Phone, Email
# (ISBN is not searchable because this domestic library does not store ISBNs;
#  Category and Email fill that role instead.)
#
# Results from both tables are merged into ONE uniform list so the UI can show
# them together:
#     {"type": "Book"|"Borrower", "name": ..., "details": ..., "status": ...}
# For a book that is currently out, the holder's name is added to `details`,
# which directly answers "who has my book?".
#
# Returns the standard response dict: {success, message, data}.
# ============================================================================

from database.connection import Database
from utils.logger import logger


class SearchService:
    """Cross-table keyword search over books and borrowers."""

    @staticmethod
    def _response(success, message, data=None):
        return {"success": success, "message": message, "data": data}

    def universal_search(self, keyword):
        """
        Search books and borrowers by a single keyword. An empty keyword
        returns an empty result set (nothing to show yet).
        """
        kw = (keyword or "").strip()
        if not kw:
            return self._response(True, "Type to search…", [])

        like = f"%{kw}%"
        try:
            with Database() as db:
                # Books (with the current holder, if the book is out).
                books = db.execute_query(
                    "SELECT b.Title, b.Author, b.Category, b.Status, br.Name "
                    "FROM Books b "
                    "LEFT JOIN Transactions t "
                    "       ON t.BookID = b.BookID AND t.ReturnDate IS NULL "
                    "LEFT JOIN Borrowers br ON br.BorrowerID = t.BorrowerID "
                    "WHERE b.Status <> 'Removed' "
                    "  AND (b.Title LIKE ? OR b.Author LIKE ? "
                    "       OR b.Category LIKE ? OR b.Status LIKE ?) "
                    "ORDER BY b.Title",
                    (like, like, like, like),
                )
                # Borrowers.
                people = db.execute_query(
                    "SELECT Name, Phone, Email FROM Borrowers "
                    "WHERE IsActive = 1 "
                    "  AND (Name LIKE ? OR Phone LIKE ? OR Email LIKE ?) "
                    "ORDER BY Name",
                    (like, like, like),
                )

            results = []
            for title, author, category, status, holder in books:
                details = " · ".join(x for x in (author, category) if x)
                if status == "Issued" and holder:
                    details += (" " if details else "") + f"(with {holder})"
                results.append({
                    "type": "Book",
                    "name": title,
                    "details": details,
                    "status": status,
                })
            for name, phone, email in people:
                details = " · ".join(x for x in (phone, email) if x)
                results.append({
                    "type": "Borrower",
                    "name": name,
                    "details": details,
                    "status": "Active",
                })

            return self._response(True, f"{len(results)} result(s) for '{kw}'.", results)
        except Exception as error:
            logger.error(f"universal_search failed (keyword={kw!r}): {error}")
            return self._response(False, "Search failed. Please try again.")
