# ============================================================================
# services/statistics_service.py
# ----------------------------------------------------------------------------
# STATISTICS SERVICE — library analytics built on SQL aggregate queries.
#
# Calculates:
#   total_books        - active catalog (not 'Removed')              COUNT
#   borrowed_books     - status 'Issued'                            COUNT
#   available_books    - status 'Available'                         COUNT
#   total_borrowers    - active borrowers                           COUNT
#   per_person         - books borrowed per person        GROUP BY + COUNT
#   top_author         - most borrowed author           GROUP BY + TOP 1
#   top_category       - most borrowed category          GROUP BY + TOP 1
#
# Everything is computed in the database with aggregate SQL (COUNT, GROUP BY,
# TOP 1) — not in Python — and returned as one dict.
#
# Returns the standard response dict: {success, message, data}.
# ============================================================================

from database.connection import Database
from utils.logger import logger


class StatisticsService:
    """Aggregate statistics about the library's books and borrowing."""

    @staticmethod
    def _response(success, message, data=None):
        return {"success": success, "message": message, "data": data}

    def get_statistics(self):
        """
        Run every statistic in a single connection and return them together.

        data = {
            total_books, borrowed_books, available_books, total_borrowers,
            per_person:   [{"name": str, "count": int}, ...],
            top_author:   {"author": str, "count": int}   or None,
            top_category: {"category": str, "count": int} or None,
        }
        """
        try:
            with Database() as db:
                # --- Headline counts (scalar aggregates) -------------------
                counts = db.fetch_one(
                    "SELECT "
                    "  (SELECT COUNT(*) FROM Books WHERE Status <> 'Removed'), "
                    "  (SELECT COUNT(*) FROM Books WHERE Status = 'Issued'), "
                    "  (SELECT COUNT(*) FROM Books WHERE Status = 'Available'), "
                    "  (SELECT COUNT(*) FROM Borrowers WHERE IsActive = 1)"
                )

                # --- Books borrowed per person (GROUP BY + COUNT) ----------
                # LEFT JOIN so active borrowers with zero loans still appear.
                per_person_rows = db.execute_query(
                    "SELECT br.Name, COUNT(t.TransactionID) AS Borrowed "
                    "FROM Borrowers br "
                    "LEFT JOIN Transactions t ON t.BorrowerID = br.BorrowerID "
                    "WHERE br.IsActive = 1 "
                    "GROUP BY br.BorrowerID, br.Name "
                    "ORDER BY Borrowed DESC, br.Name"
                )

                # --- Most borrowed author (GROUP BY + TOP 1) ---------------
                author_row = db.fetch_one(
                    "SELECT TOP 1 b.Author, COUNT(t.TransactionID) AS Borrowed "
                    "FROM Books b "
                    "JOIN Transactions t ON t.BookID = b.BookID "
                    "WHERE b.Author IS NOT NULL AND LTRIM(RTRIM(b.Author)) <> '' "
                    "GROUP BY b.Author "
                    "ORDER BY Borrowed DESC"
                )

                # --- Most borrowed category (GROUP BY + TOP 1) -------------
                category_row = db.fetch_one(
                    "SELECT TOP 1 b.Category, COUNT(t.TransactionID) AS Borrowed "
                    "FROM Books b "
                    "JOIN Transactions t ON t.BookID = b.BookID "
                    "WHERE b.Category IS NOT NULL AND LTRIM(RTRIM(b.Category)) <> '' "
                    "GROUP BY b.Category "
                    "ORDER BY Borrowed DESC"
                )

            data = {
                "total_books": counts[0],
                "borrowed_books": counts[1],
                "available_books": counts[2],
                "total_borrowers": counts[3],
                "per_person": [{"name": r[0], "count": r[1]} for r in per_person_rows],
                "top_author": ({"author": author_row[0], "count": author_row[1]}
                               if author_row else None),
                "top_category": ({"category": category_row[0], "count": category_row[1]}
                                 if category_row else None),
            }
            return self._response(True, "Statistics calculated.", data)
        except Exception as error:
            logger.error(f"get_statistics failed: {error}")
            return self._response(False, "Could not calculate the statistics.")
