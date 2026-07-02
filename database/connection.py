# ============================================================================
# database/connection.py
# ----------------------------------------------------------------------------
# DATABASE CONNECTION MANAGER (SQL Server via pyodbc).
#
# Provides a single reusable `Database` class that every repository uses to
# talk to SQL Server. It is the ONLY place in the codebase that imports pyodbc
# or opens a connection — so connection logic lives in exactly one spot.
#
# Features:
#   - Reads the connection string from config/settings.py
#   - Connects automatically on creation
#   - Can be used as a context manager (`with Database() as db:`) for safe close
#   - execute_query()      -> run a SELECT and return the fetched rows
#   - fetch_one()          -> run a SELECT and return a single row
#   - execute_non_query()  -> run INSERT/UPDATE/DELETE and commit
#   - Centralized exception handling with clear error messages
# ============================================================================

import pyodbc

from config.settings import get_connection_string


class Database:
    """
    Reusable wrapper around a pyodbc connection to SQL Server.

    Typical usage (context manager — recommended, auto-closes):

        with Database() as db:
            rows = db.execute_query("SELECT * FROM Books")
            db.execute_non_query(
                "INSERT INTO Books (Title, Author) VALUES (?, ?)",
                ("Dune", "Frank Herbert"),
            )

    Or manually:

        db = Database()
        rows = db.execute_query("SELECT * FROM Books")
        db.close()
    """

    def __init__(self, autoconnect: bool = True):
        """
        Create the Database object. By default it connects immediately so the
        object is ready to use right away.
        """
        self.connection = None      # the live pyodbc connection
        self.cursor = None          # the cursor used to run statements
        if autoconnect:
            self.connect()

    # ------------------------------------------------------------------ #
    # Connection lifecycle
    # ------------------------------------------------------------------ #
    def connect(self):
        """
        Open a connection to SQL Server using the string from settings.py.
        Raises a clear error if the connection cannot be established.
        """
        try:
            self.connection = pyodbc.connect(get_connection_string())
            self.cursor = self.connection.cursor()
        except pyodbc.Error as error:
            # Wrap the low-level driver error in a readable message.
            raise ConnectionError(
                f"Failed to connect to SQL Server. "
                f"Check DB_CONFIG in config/settings.py.\nDetails: {error}"
            )

    def close(self):
        """
        Close the cursor and connection safely. Never raises — closing an
        already-closed or never-opened connection is a no-op.
        """
        try:
            if self.cursor is not None:
                self.cursor.close()
            if self.connection is not None:
                self.connection.close()
        except pyodbc.Error:
            # Nothing useful to do if closing fails; just ignore it.
            pass
        finally:
            self.cursor = None
            self.connection = None

    # ------------------------------------------------------------------ #
    # Context-manager support:  `with Database() as db:`
    # ------------------------------------------------------------------ #
    def __enter__(self):
        # Ensure we have a live connection when entering the block.
        if self.connection is None:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Always close, whether the block succeeded or raised.
        self.close()

    # ------------------------------------------------------------------ #
    # Read operations (SELECT)
    # ------------------------------------------------------------------ #
    def execute_query(self, query: str, params: tuple = ()):
        """
        Run a SELECT statement and return ALL matching rows.

        query  : SQL text, using '?' placeholders for parameters.
        params : values to bind to the placeholders (prevents SQL injection).
        returns: a list of pyodbc.Row objects (empty list if no matches).
        """
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except pyodbc.Error as error:
            raise RuntimeError(f"Query failed: {query}\nDetails: {error}")

    def fetch_one(self, query: str, params: tuple = ()):
        """
        Run a SELECT statement and return only the FIRST row (or None).
        Handy for lookups by id or COUNT(*) style queries.
        """
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchone()
        except pyodbc.Error as error:
            raise RuntimeError(f"Query failed: {query}\nDetails: {error}")

    # ------------------------------------------------------------------ #
    # Write operations (INSERT / UPDATE / DELETE)
    # ------------------------------------------------------------------ #
    def execute_non_query(self, query: str, params: tuple = ()) -> int:
        """
        Run an INSERT / UPDATE / DELETE statement and COMMIT the change.

        returns: the number of rows affected.
        On error, the transaction is rolled back so the database is not left
        in a half-changed state.
        """
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
            return self.cursor.rowcount
        except pyodbc.Error as error:
            # Undo the partial change before re-raising.
            if self.connection is not None:
                self.connection.rollback()
            raise RuntimeError(f"Statement failed: {query}\nDetails: {error}")

    def execute_insert(self, query: str, params: tuple = ()):
        """
        Run an INSERT and return the new row's identity value (the generated
        primary key). Useful right after adding a book/borrower/transaction.

        Note: appends 'SELECT SCOPE_IDENTITY()' to read back the new id in the
        same batch, so it reflects THIS insert only.
        """
        try:
            self.cursor.execute(query + "; SELECT SCOPE_IDENTITY();", params)
            # Move to the result set that holds the new identity value.
            self.cursor.nextset()
            new_id = self.cursor.fetchone()[0]
            self.connection.commit()
            return int(new_id) if new_id is not None else None
        except pyodbc.Error as error:
            if self.connection is not None:
                self.connection.rollback()
            raise RuntimeError(f"Insert failed: {query}\nDetails: {error}")
