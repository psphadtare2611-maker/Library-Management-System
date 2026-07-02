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

from database.connection import Database
from models.transaction import Transaction


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
