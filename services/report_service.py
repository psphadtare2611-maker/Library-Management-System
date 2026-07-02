# ============================================================================
# services/report_service.py
# ----------------------------------------------------------------------------
# REPORT SERVICE — aggregated numbers and reports for the app.
#
# Implemented now:
#   - get_dashboard_stats() -> the summary counts shown on the Dashboard.
#
# To come (Reports screen):
#   - currently_borrowed(), overdue_report(), most_borrowed_books(),
#     borrower_summary()
#
# Talks to SQL Server through the reusable Database class and returns the
# standard response dict: {success, message, data}.
# ============================================================================

from database.connection import Database


class ReportService:
    """Aggregated statistics and reports."""

    @staticmethod
    def _response(success, message, data=None):
        return {"success": success, "message": message, "data": data}

    # ------------------------------------------------------------------ #
    # DASHBOARD SUMMARY
    # ------------------------------------------------------------------ #
    def get_dashboard_stats(self):
        """
        Return the headline counts for the Dashboard cards, in one round trip:
            total_books      - active catalog (not 'Removed')
            available_books  - status 'Available'
            borrowed_books   - status 'Issued'
            borrowers        - active borrowers
            today_transactions - issues or returns dated today

        Data is a dict with those keys. On failure, returns success=False.
        """
        try:
            query = (
                "SELECT "
                "  (SELECT COUNT(*) FROM Books WHERE Status <> 'Removed'), "
                "  (SELECT COUNT(*) FROM Books WHERE Status = 'Available'), "
                "  (SELECT COUNT(*) FROM Books WHERE Status = 'Issued'), "
                "  (SELECT COUNT(*) FROM Borrowers WHERE IsActive = 1), "
                "  (SELECT COUNT(*) FROM Transactions "
                "     WHERE IssueDate = CAST(GETDATE() AS DATE) "
                "        OR ReturnDate = CAST(GETDATE() AS DATE))"
            )
            with Database() as db:
                row = db.fetch_one(query)

            stats = {
                "total_books": row[0],
                "available_books": row[1],
                "borrowed_books": row[2],
                "borrowers": row[3],
                "today_transactions": row[4],
            }
            return self._response(True, "Dashboard stats loaded.", stats)
        except Exception as error:
            return self._response(False, f"Could not load dashboard stats: {error}")
