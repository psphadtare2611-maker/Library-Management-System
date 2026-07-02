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
from utils.logger import logger


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
            logger.error(f"get_dashboard_stats failed: {error}")
            return self._response(False, "Could not load the dashboard statistics.")

    # ------------------------------------------------------------------ #
    # Generic report runner
    # ------------------------------------------------------------------ #
    def _run_report(self, label, columns, query, params=()):
        """
        Execute a report query and package it uniformly.

        columns : list of (heading, width) describing each column, in the same
                  order the SELECT returns them.
        Returns data = {"columns": [(heading, width)...], "rows": [tuple...]}
        so the UI can build a Treeview and pandas can build a DataFrame.
        """
        try:
            with Database() as db:
                raw = db.execute_query(query, params)
            # Convert pyodbc.Row objects to plain tuples (nicer for pandas).
            rows = [tuple(r) for r in raw]
            data = {"columns": columns, "rows": rows}
            return self._response(True, f"{label}: {len(rows)} row(s).", data)
        except Exception as error:
            logger.error(f"report '{label}' failed: {error}")
            return self._response(False, f"Could not build the '{label}' report.")

    # ------------------------------------------------------------------ #
    # Individual reports
    # ------------------------------------------------------------------ #
    def available_books(self):
        """Books currently available to lend."""
        columns = [("Title", 240), ("Author", 180), ("Category", 130), ("Purchase Date", 120)]
        query = (
            "SELECT Title, Author, Category, PurchaseDate "
            "FROM Books WHERE Status = 'Available' ORDER BY Title"
        )
        return self._run_report("Available Books", columns, query)

    def borrowed_books(self):
        """Books that are currently out, with who has them and the due date."""
        columns = [("Title", 220), ("Author", 150), ("Borrower", 150),
                   ("Issue Date", 110), ("Due Date", 110)]
        query = (
            "SELECT b.Title, b.Author, br.Name, t.IssueDate, t.ExpectedReturnDate "
            "FROM Transactions t "
            "JOIN Books b      ON t.BookID = b.BookID "
            "JOIN Borrowers br ON t.BorrowerID = br.BorrowerID "
            "WHERE t.ReturnDate IS NULL "
            "ORDER BY t.ExpectedReturnDate"
        )
        return self._run_report("Borrowed Books", columns, query)

    def overdue_books(self):
        """Currently-out books whose due date has passed."""
        columns = [("Title", 230), ("Borrower", 160), ("Due Date", 120), ("Days Overdue", 110)]
        query = (
            "SELECT b.Title, br.Name, t.ExpectedReturnDate, "
            "       DATEDIFF(day, t.ExpectedReturnDate, CAST(GETDATE() AS DATE)) "
            "FROM Transactions t "
            "JOIN Books b      ON t.BookID = b.BookID "
            "JOIN Borrowers br ON t.BorrowerID = br.BorrowerID "
            "WHERE t.ReturnDate IS NULL "
            "  AND t.ExpectedReturnDate < CAST(GETDATE() AS DATE) "
            "ORDER BY DATEDIFF(day, t.ExpectedReturnDate, CAST(GETDATE() AS DATE)) DESC"
        )
        return self._run_report("Overdue Books", columns, query)

    def borrow_history(self):
        """The complete borrowing log (issued and returned)."""
        columns = [("Title", 200), ("Borrower", 150), ("Issue Date", 100),
                   ("Due Date", 100), ("Return Date", 100), ("Status", 90)]
        query = (
            "SELECT b.Title, br.Name, t.IssueDate, t.ExpectedReturnDate, "
            "       t.ReturnDate, t.Status "
            "FROM Transactions t "
            "JOIN Books b      ON t.BookID = b.BookID "
            "JOIN Borrowers br ON t.BorrowerID = br.BorrowerID "
            "ORDER BY t.IssueDate DESC, t.TransactionID DESC"
        )
        return self._run_report("Borrow History", columns, query)

    def most_borrowed_books(self):
        """Books ranked by how many times they have been borrowed."""
        columns = [("Title", 260), ("Author", 200), ("Times Borrowed", 130)]
        query = (
            "SELECT b.Title, b.Author, COUNT(t.TransactionID) AS Times "
            "FROM Books b "
            "JOIN Transactions t ON b.BookID = t.BookID "
            "WHERE b.Status <> 'Removed' "
            "GROUP BY b.BookID, b.Title, b.Author "
            "ORDER BY Times DESC, b.Title"
        )
        return self._run_report("Most Borrowed Books", columns, query)
