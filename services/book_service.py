# ============================================================================
# services/book_service.py
# ----------------------------------------------------------------------------
# BOOK SERVICE — business logic for managing books.
#
# Talks to SQL Server through the reusable Database class (database/connection).
# The UI calls this service; it never touches the database directly.
#
# Every method returns a MEANINGFUL RESPONSE dict so the UI can react without
# guessing:
#       { "success": True/False, "message": "...", "data": <result or None> }
#   - data is a Book (or list of Books) for read operations,
#     the new BookID for add, or None otherwise.
#
# All database access is wrapped in try/except so a driver/SQL error becomes a
# clean {"success": False, ...} response instead of crashing the app.
# ============================================================================

from database.connection import Database
from models.book import Book


class BookService:
    """Business logic for adding, editing, removing and finding books."""

    # -- SELECT column list, kept in ONE place so every read is consistent. --
    # Order matters: it must match _row_to_book() below.
    _COLUMNS = "BookID, Title, Author, Category, PurchaseDate, Status, Remarks"

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _response(success, message, data=None):
        """Build the standard response dict returned by every method."""
        return {"success": success, "message": message, "data": data}

    @staticmethod
    def _row_to_book(row):
        """Convert a pyodbc row (in _COLUMNS order) into a Book object."""
        return Book(
            book_id=row[0],
            title=row[1],
            author=row[2],
            category=row[3],
            purchase_date=row[4],
            status=row[5],
            remarks=row[6],
        )

    # ------------------------------------------------------------------ #
    # CREATE
    # ------------------------------------------------------------------ #
    def add_book(self, book):
        """
        Insert a new book. `book` is a validated Book object (validation runs
        in the Book constructor, so an invalid book never reaches here).

        Returns the new BookID in `data` on success.
        """
        try:
            query = (
                "INSERT INTO Books (Title, Author, Category, PurchaseDate, Status, Remarks) "
                "VALUES (?, ?, ?, ?, ?, ?)"
            )
            params = (
                book.title,
                book.author,
                book.category,
                book.purchase_date,
                book.status,
                book.remarks,
            )
            with Database() as db:
                new_id = db.execute_insert(query, params)
            return self._response(True, f"Book '{book.title}' added successfully.", new_id)
        except Exception as error:
            return self._response(False, f"Could not add book: {error}")

    # ------------------------------------------------------------------ #
    # UPDATE
    # ------------------------------------------------------------------ #
    def update_book(self, book):
        """
        Update an existing book. `book` must carry its book_id (the hidden id
        of the record being edited).

        Returns success only if a row was actually changed.
        """
        if book.book_id is None:
            return self._response(False, "Cannot update a book without its id.")

        try:
            query = (
                "UPDATE Books "
                "SET Title = ?, Author = ?, Category = ?, PurchaseDate = ?, "
                "    Status = ?, Remarks = ? "
                "WHERE BookID = ?"
            )
            params = (
                book.title,
                book.author,
                book.category,
                book.purchase_date,
                book.status,
                book.remarks,
                book.book_id,
            )
            with Database() as db:
                rows = db.execute_non_query(query, params)

            if rows == 0:
                return self._response(False, f"No book found with id {book.book_id}.")
            return self._response(True, f"Book '{book.title}' updated successfully.")
        except Exception as error:
            return self._response(False, f"Could not update book: {error}")

    # ------------------------------------------------------------------ #
    # DELETE (soft delete)
    # ------------------------------------------------------------------ #
    def delete_book(self, book_id):
        """
        Remove a book. This is a SOFT delete: the row is kept and its Status
        set to 'Removed', so borrowing history stays intact.

        Guard rule: a book that is currently 'Issued' cannot be removed.
        """
        try:
            with Database() as db:
                # First confirm the book exists and check its current status.
                row = db.fetch_one(
                    "SELECT Title, Status FROM Books WHERE BookID = ?", (book_id,)
                )
                if row is None:
                    return self._response(False, f"No book found with id {book_id}.")

                title, status = row[0], row[1]
                if status == "Issued":
                    return self._response(
                        False,
                        f"'{title}' is currently issued and cannot be removed. "
                        f"Return it first.",
                    )
                if status == "Removed":
                    return self._response(False, f"'{title}' is already removed.")

                db.execute_non_query(
                    "UPDATE Books SET Status = 'Removed' WHERE BookID = ?", (book_id,)
                )
            return self._response(True, f"Book '{title}' removed successfully.")
        except Exception as error:
            return self._response(False, f"Could not remove book: {error}")

    # ------------------------------------------------------------------ #
    # READ — single book
    # ------------------------------------------------------------------ #
    def get_book(self, book_id):
        """Fetch one book by its id. Returns the Book in `data`, or a failure."""
        try:
            with Database() as db:
                row = db.fetch_one(
                    f"SELECT {self._COLUMNS} FROM Books WHERE BookID = ?", (book_id,)
                )
            if row is None:
                return self._response(False, f"No book found with id {book_id}.")
            return self._response(True, "Book found.", self._row_to_book(row))
        except Exception as error:
            return self._response(False, f"Could not fetch book: {error}")

    # ------------------------------------------------------------------ #
    # READ — search
    # ------------------------------------------------------------------ #
    def search_book(self, keyword):
        """
        Search books by Title, Author, or Category (case-insensitive LIKE).
        Removed books are excluded. Returns a list of Books in `data`
        (empty list if nothing matches).
        """
        try:
            like = f"%{keyword.strip()}%"
            query = (
                f"SELECT {self._COLUMNS} FROM Books "
                "WHERE Status <> 'Removed' "
                "AND (Title LIKE ? OR Author LIKE ? OR Category LIKE ?) "
                "ORDER BY Title"
            )
            with Database() as db:
                rows = db.execute_query(query, (like, like, like))
            books = [self._row_to_book(r) for r in rows]
            return self._response(True, f"{len(books)} book(s) found.", books)
        except Exception as error:
            return self._response(False, f"Search failed: {error}")

    # ------------------------------------------------------------------ #
    # READ — all books
    # ------------------------------------------------------------------ #
    def get_all_books(self):
        """
        Fetch the whole active catalog (everything not 'Removed'), sorted by
        title. Returns a list of Books in `data`.
        """
        try:
            query = (
                f"SELECT {self._COLUMNS} FROM Books "
                "WHERE Status <> 'Removed' "
                "ORDER BY Title"
            )
            with Database() as db:
                rows = db.execute_query(query)
            books = [self._row_to_book(r) for r in rows]
            return self._response(True, f"{len(books)} book(s) in the library.", books)
        except Exception as error:
            return self._response(False, f"Could not fetch books: {error}")
