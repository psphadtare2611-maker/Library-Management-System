# ============================================================================
# services/borrower_service.py
# ----------------------------------------------------------------------------
# BORROWER SERVICE — business logic for managing borrowers (friends).
#
# Talks to SQL Server through the reusable Database class (database/connection).
# Mirrors BookService: every method returns a MEANINGFUL RESPONSE dict:
#       { "success": True/False, "message": "...", "data": <result or None> }
#   - data is a Borrower (or list of Borrowers) for reads, the new BorrowerID
#     for add, or None otherwise.
#
# Delete is a SOFT delete (IsActive = 0) so borrowing history is preserved,
# and it is refused for anyone who currently holds a book.
# ============================================================================

from database.connection import Database
from models.borrower import Borrower


class BorrowerService:
    """Business logic for adding, editing, removing and finding borrowers."""

    # SELECT column list, in one place. Order must match _row_to_borrower().
    _COLUMNS = "BorrowerID, Name, Phone, Email, Address"

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _response(success, message, data=None):
        """Build the standard response dict returned by every method."""
        return {"success": success, "message": message, "data": data}

    @staticmethod
    def _row_to_borrower(row):
        """Convert a pyodbc row (in _COLUMNS order) into a Borrower object."""
        return Borrower(
            borrower_id=row[0],
            name=row[1],
            phone=row[2],
            email=row[3],
            address=row[4],
        )

    # ------------------------------------------------------------------ #
    # CREATE
    # ------------------------------------------------------------------ #
    def add_borrower(self, borrower):
        """
        Insert a new borrower. `borrower` is a validated Borrower object
        (validation runs in the Borrower constructor).

        Returns the new BorrowerID in `data` on success.
        """
        try:
            query = (
                "INSERT INTO Borrowers (Name, Phone, Email, Address) "
                "VALUES (?, ?, ?, ?)"
            )
            params = (borrower.name, borrower.phone, borrower.email, borrower.address)
            with Database() as db:
                new_id = db.execute_insert(query, params)
            return self._response(True, f"Borrower '{borrower.name}' added successfully.", new_id)
        except Exception as error:
            return self._response(False, f"Could not add borrower: {error}")

    # ------------------------------------------------------------------ #
    # UPDATE
    # ------------------------------------------------------------------ #
    def update_borrower(self, borrower):
        """
        Update an existing borrower. `borrower` must carry its borrower_id.
        Returns success only if a row was actually changed.
        """
        if borrower.borrower_id is None:
            return self._response(False, "Cannot update a borrower without its id.")

        try:
            query = (
                "UPDATE Borrowers "
                "SET Name = ?, Phone = ?, Email = ?, Address = ? "
                "WHERE BorrowerID = ? AND IsActive = 1"
            )
            params = (
                borrower.name,
                borrower.phone,
                borrower.email,
                borrower.address,
                borrower.borrower_id,
            )
            with Database() as db:
                rows = db.execute_non_query(query, params)

            if rows == 0:
                return self._response(False, f"No active borrower found with id {borrower.borrower_id}.")
            return self._response(True, f"Borrower '{borrower.name}' updated successfully.")
        except Exception as error:
            return self._response(False, f"Could not update borrower: {error}")

    # ------------------------------------------------------------------ #
    # DELETE (soft delete)
    # ------------------------------------------------------------------ #
    def delete_borrower(self, borrower_id):
        """
        Remove a borrower. This is a SOFT delete: IsActive is set to 0 so the
        row (and their borrowing history) is preserved.

        Guard rule: a borrower who currently holds a book (an unreturned
        transaction) cannot be removed.
        """
        try:
            with Database() as db:
                # Confirm the borrower exists and is still active.
                row = db.fetch_one(
                    "SELECT Name, IsActive FROM Borrowers WHERE BorrowerID = ?",
                    (borrower_id,),
                )
                if row is None:
                    return self._response(False, f"No borrower found with id {borrower_id}.")

                name, is_active = row[0], row[1]
                if not is_active:
                    return self._response(False, f"'{name}' has already been removed.")

                # Refuse if they still have a book out (unreturned transaction).
                active_loan = db.fetch_one(
                    "SELECT COUNT(*) FROM Transactions "
                    "WHERE BorrowerID = ? AND ReturnDate IS NULL",
                    (borrower_id,),
                )
                if active_loan and active_loan[0] > 0:
                    return self._response(
                        False,
                        f"'{name}' currently has {active_loan[0]} book(s) out and "
                        f"cannot be removed until they are returned.",
                    )

                db.execute_non_query(
                    "UPDATE Borrowers SET IsActive = 0 WHERE BorrowerID = ?",
                    (borrower_id,),
                )
            return self._response(True, f"Borrower '{name}' removed successfully.")
        except Exception as error:
            return self._response(False, f"Could not remove borrower: {error}")

    # ------------------------------------------------------------------ #
    # READ — single borrower (bonus helper, used by edit flows)
    # ------------------------------------------------------------------ #
    def get_borrower(self, borrower_id):
        """Fetch one active borrower by id. Returns the Borrower in `data`."""
        try:
            with Database() as db:
                row = db.fetch_one(
                    f"SELECT {self._COLUMNS} FROM Borrowers "
                    "WHERE BorrowerID = ? AND IsActive = 1",
                    (borrower_id,),
                )
            if row is None:
                return self._response(False, f"No active borrower found with id {borrower_id}.")
            return self._response(True, "Borrower found.", self._row_to_borrower(row))
        except Exception as error:
            return self._response(False, f"Could not fetch borrower: {error}")

    # ------------------------------------------------------------------ #
    # READ — search
    # ------------------------------------------------------------------ #
    def search_borrower(self, keyword):
        """
        Search active borrowers by Name, Phone, or Email (case-insensitive
        LIKE). Returns a list of Borrowers in `data` (empty if none match).
        """
        try:
            like = f"%{keyword.strip()}%"
            query = (
                f"SELECT {self._COLUMNS} FROM Borrowers "
                "WHERE IsActive = 1 "
                "AND (Name LIKE ? OR Phone LIKE ? OR Email LIKE ?) "
                "ORDER BY Name"
            )
            with Database() as db:
                rows = db.execute_query(query, (like, like, like))
            borrowers = [self._row_to_borrower(r) for r in rows]
            return self._response(True, f"{len(borrowers)} borrower(s) found.", borrowers)
        except Exception as error:
            return self._response(False, f"Search failed: {error}")

    # ------------------------------------------------------------------ #
    # READ — all borrowers
    # ------------------------------------------------------------------ #
    def get_all_borrowers(self):
        """
        Fetch all active borrowers, sorted by name. Returns a list of
        Borrowers in `data`.
        """
        try:
            query = (
                f"SELECT {self._COLUMNS} FROM Borrowers "
                "WHERE IsActive = 1 "
                "ORDER BY Name"
            )
            with Database() as db:
                rows = db.execute_query(query)
            borrowers = [self._row_to_borrower(r) for r in rows]
            return self._response(True, f"{len(borrowers)} borrower(s) registered.", borrowers)
        except Exception as error:
            return self._response(False, f"Could not fetch borrowers: {error}")
