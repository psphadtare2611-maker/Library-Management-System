# ============================================================================
# services/circulation_service.py
# ----------------------------------------------------------------------------
# CIRCULATION SERVICE — the heart of the application: issuing (and, later,
# returning) books.
#
# issue_book() enforces the full workflow as ONE atomic operation:
#     1. Verify the book exists.
#     2. Verify the borrower exists and is active.
#     3. Verify the book's status is 'Available' (this prevents issuing a
#        book that is already out -> no duplicate issuing).
#     4. Insert the transaction (Status='Issued', ReturnDate=NULL).
#     5. Update the book's status to 'Issued'.
# Steps 4 and 5 are committed together; if anything fails, the whole thing is
# rolled back so the database is never left half-updated.
#
# NOTE on wording: the book's "borrowed" state is stored as status 'Issued'
# (the value allowed by the schema's CHECK constraint and the Book model).
#
# Returns the standard response dict: {success, message, data}.
# ============================================================================

from datetime import date

from database.connection import Database
from models.transaction import Transaction
from utils.logger import logger


class CirculationService:
    """Business logic for issuing books (and returning them, later)."""

    @staticmethod
    def _response(success, message, data=None):
        return {"success": success, "message": message, "data": data}

    # ------------------------------------------------------------------ #
    # ISSUE
    # ------------------------------------------------------------------ #
    def issue_book(self, book_id, borrower_id, issue_date, expected_return_date, remarks=None):
        """
        Issue a book to a borrower.

        book_id, borrower_id : the hidden internal ids (from the dropdowns).
        issue_date, expected_return_date : date objects or 'YYYY-MM-DD' strings.
        remarks : optional note.

        Returns the new TransactionID in `data` on success.
        """
        # --- Validate the dates/shape up front via the Transaction model ---
        try:
            tx = Transaction(
                book_id=book_id,
                borrower_id=borrower_id,
                issue_date=issue_date,
                expected_return_date=expected_return_date,
                remarks=remarks,
            )
        except ValueError as validation_error:
            return self._response(False, str(validation_error))

        # --- Do all the checks + writes on a single connection (atomic) ----
        try:
            with Database() as db:
                cursor = db.cursor

                # (1) Book must exist.
                book = cursor.execute(
                    "SELECT Title, Status FROM Books WHERE BookID = ?", (book_id,)
                ).fetchone()
                if book is None:
                    return self._response(False, "The selected book does not exist.")
                title, book_status = book[0], book[1]

                # (2) Borrower must exist and be active.
                borrower = cursor.execute(
                    "SELECT Name, IsActive FROM Borrowers WHERE BorrowerID = ?",
                    (borrower_id,),
                ).fetchone()
                if borrower is None:
                    return self._response(False, "The selected borrower does not exist.")
                borrower_name, is_active = borrower[0], borrower[1]
                if not is_active:
                    return self._response(False, f"Borrower '{borrower_name}' is inactive.")

                # (3) Book must be Available (prevents duplicate issuing).
                if book_status != "Available":
                    if book_status == "Issued":
                        msg = f"'{title}' is already issued and cannot be issued again."
                    else:
                        msg = f"'{title}' cannot be issued (current status: {book_status})."
                    return self._response(False, msg)

                # (4) Insert the transaction and read back its new id.
                cursor.execute(
                    "INSERT INTO Transactions "
                    "(BookID, BorrowerID, IssueDate, ExpectedReturnDate, Status, Remarks) "
                    "VALUES (?, ?, ?, ?, 'Issued', ?); "
                    "SELECT SCOPE_IDENTITY();",
                    (book_id, borrower_id, tx.issue_date, tx.expected_return_date, tx.remarks),
                )
                cursor.nextset()
                new_id = cursor.fetchone()[0]

                # (5) Mark the book as issued.
                cursor.execute(
                    "UPDATE Books SET Status = 'Issued' WHERE BookID = ?", (book_id,)
                )

                # Commit steps 4 and 5 together.
                db.connection.commit()

            logger.info(
                f"Book issued: '{title}' to '{borrower_name}' "
                f"(tx={int(new_id) if new_id is not None else '?'}, "
                f"due {tx.expected_return_date})"
            )
            return self._response(
                True,
                f"'{title}' issued to '{borrower_name}'. "
                f"Due back on {tx.expected_return_date}.",
                int(new_id) if new_id is not None else None,
            )
        except Exception as error:
            # The connection closes on exit without a commit, so pyodbc rolls
            # back the uncommitted insert/update automatically.
            return self._response(False, f"Could not issue book: {error}")

    # ------------------------------------------------------------------ #
    # ACTIVE LOANS (books currently out) — used by the Return screen
    # ------------------------------------------------------------------ #
    def get_active_loans(self, keyword=None):
        """
        List every book currently out (ReturnDate IS NULL), joined with its
        book title and borrower name. Optionally filter by a keyword that
        matches the title or the borrower's name.

        Returns a list of dicts in `data`, each:
            {transaction_id, book_title, borrower_name,
             issue_date, expected_return_date, overdue}
        `overdue` is True if the due date has already passed.
        """
        try:
            query = (
                "SELECT t.TransactionID, b.Title, br.Name, "
                "       t.IssueDate, t.ExpectedReturnDate "
                "FROM Transactions t "
                "JOIN Books b     ON t.BookID = b.BookID "
                "JOIN Borrowers br ON t.BorrowerID = br.BorrowerID "
                "WHERE t.ReturnDate IS NULL "
            )
            params = ()
            if keyword and keyword.strip():
                like = f"%{keyword.strip()}%"
                query += "AND (b.Title LIKE ? OR br.Name LIKE ?) "
                params = (like, like)
            query += "ORDER BY t.ExpectedReturnDate"

            with Database() as db:
                rows = db.execute_query(query, params)

            today = date.today()
            loans = []
            for r in rows:
                expected = r[4]
                loans.append({
                    "transaction_id": r[0],
                    "book_title": r[1],
                    "borrower_name": r[2],
                    "issue_date": r[3],
                    "expected_return_date": expected,
                    "overdue": bool(expected and expected < today),
                })
            return self._response(True, f"{len(loans)} book(s) currently out.", loans)
        except Exception as error:
            return self._response(False, f"Could not load active loans: {error}")

    # ------------------------------------------------------------------ #
    # RETURN
    # ------------------------------------------------------------------ #
    def return_book(self, transaction_id, return_date=None):
        """
        Return a borrowed book. Atomically:
            - set the transaction's ReturnDate and Status='Returned'
            - set the book's status back to 'Available'

        return_date defaults to today. Returns a confirmation message that
        notes if the book came back late.
        """
        rdate = return_date or date.today()
        try:
            with Database() as db:
                cursor = db.cursor

                # Look up the transaction along with its book/borrower names.
                row = cursor.execute(
                    "SELECT t.BookID, t.IssueDate, t.ExpectedReturnDate, t.ReturnDate, "
                    "       b.Title, br.Name "
                    "FROM Transactions t "
                    "JOIN Books b      ON t.BookID = b.BookID "
                    "JOIN Borrowers br ON t.BorrowerID = br.BorrowerID "
                    "WHERE t.TransactionID = ?",
                    (transaction_id,),
                ).fetchone()
                if row is None:
                    return self._response(False, "That transaction does not exist.")

                book_id, issue_date, expected, existing_return, title, name = row

                # Guard: cannot return something already returned.
                if existing_return is not None:
                    return self._response(False, f"'{title}' has already been returned.")

                # Guard: return date cannot be before the issue date.
                if issue_date and rdate < issue_date:
                    return self._response(False, "Return date cannot be before the issue date.")

                # Update the transaction and free the book (atomic).
                cursor.execute(
                    "UPDATE Transactions SET ReturnDate = ?, Status = 'Returned' "
                    "WHERE TransactionID = ?",
                    (rdate, transaction_id),
                )
                cursor.execute(
                    "UPDATE Books SET Status = 'Available' WHERE BookID = ?", (book_id,)
                )
                db.connection.commit()

            late_days = (rdate - expected).days if expected and rdate > expected else 0
            message = f"'{title}' returned by '{name}'."
            if late_days > 0:
                message += f" It was {late_days} day(s) overdue."
            logger.info(
                f"Book returned: '{title}' by '{name}' (tx={transaction_id}"
                + (f", {late_days} day(s) overdue)" if late_days > 0 else ")")
            )
            return self._response(True, message, transaction_id)
        except Exception as error:
            return self._response(False, f"Could not return book: {error}")
