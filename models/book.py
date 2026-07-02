# ============================================================================
# models/book.py
# ----------------------------------------------------------------------------
# BOOK ENTITY — an object-oriented representation of one book in the library.
#
# For this DOMESTIC library we deliberately keep books simple:
#   - No ISBN (not needed for a personal collection).
#   - book_id is NOT something you type in. It is assigned automatically by
#     the database (IDENTITY primary key) and only used internally so that
#     transactions can point at the correct book. It defaults to None for a
#     brand-new book that has not been saved yet.
#
# User-facing fields: Title, Author, Category, PurchaseDate, Status, Remarks.
#
# This class holds data and validates it. It contains NO SQL — persistence
# is the repository's job.
# ============================================================================

from datetime import date, datetime


class Book:
    """A single book in the home library."""

    # The states a book may be in. Named constants avoid magic strings and are
    # kept in sync with the CHECK constraint in database/schema.sql.
    AVAILABLE = "Available"
    ISSUED = "Issued"
    LOST = "Lost"
    REMOVED = "Removed"
    VALID_STATUSES = (AVAILABLE, ISSUED, LOST, REMOVED)

    # Maximum field lengths, mirroring the NVARCHAR sizes in schema.sql, so we
    # give a friendly message instead of a truncation error from the database.
    MAX_TITLE = 200
    MAX_AUTHOR = 150
    MAX_CATEGORY = 50
    MAX_REMARKS = 500

    def __init__(
        self,
        title,
        author=None,
        category=None,
        purchase_date=None,
        status="Available",
        remarks=None,
        book_id=None,          # internal DB id; None until saved
    ):
        """
        Create a Book.

        title         : required — the book's title.
        author        : optional — who wrote it.
        category      : optional — genre/shelf (e.g. "Fiction").
        purchase_date : optional — a datetime.date or an 'YYYY-MM-DD' string.
        status        : one of VALID_STATUSES; new books default to Available.
        remarks       : optional — free notes (condition, edition, etc.).
        book_id       : set by the database; leave as None when creating new.
        """
        self.book_id = book_id
        self.title = title.strip() if isinstance(title, str) else title
        self.author = author.strip() if isinstance(author, str) else author
        self.category = category.strip() if isinstance(category, str) else category
        self.purchase_date = self._coerce_date(purchase_date)
        self.status = status
        self.remarks = remarks.strip() if isinstance(remarks, str) else remarks

        # Validate immediately so an invalid Book can never exist.
        self.validate()

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def validate(self):
        """
        Check that the book's data makes sense. Raises ValueError with a clear
        message on the first problem found. Called automatically on creation.
        """
        # Title is the only truly required field for a home library.
        if not self.title or not str(self.title).strip():
            raise ValueError("Book title is required and cannot be empty.")

        # Field lengths must fit the database columns.
        self._check_length("Title", self.title, self.MAX_TITLE)
        self._check_length("Author", self.author, self.MAX_AUTHOR)
        self._check_length("Category", self.category, self.MAX_CATEGORY)
        self._check_length("Remarks", self.remarks, self.MAX_REMARKS)

        # Status must be one of the known states.
        if self.status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{self.status}'. "
                f"Must be one of: {', '.join(self.VALID_STATUSES)}."
            )

        # If a purchase date was given, it must be a real date and not future.
        if self.purchase_date is not None:
            if not isinstance(self.purchase_date, date):
                raise ValueError("PurchaseDate must be a valid date.")
            if self.purchase_date > date.today():
                raise ValueError("PurchaseDate cannot be in the future.")

        return True

    @staticmethod
    def _check_length(field, value, maximum):
        """Raise ValueError if a text field is longer than the DB column."""
        if value is not None and len(value) > maximum:
            raise ValueError(f"{field} is too long (max {maximum} characters).")

    @staticmethod
    def _coerce_date(value):
        """
        Accept either a date object or an 'YYYY-MM-DD' string and return a
        date. None stays None. Raises ValueError on an unparseable string.
        """
        if value is None or isinstance(value, date):
            return value
        if isinstance(value, str):
            try:
                return datetime.strptime(value.strip(), "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("PurchaseDate must be in 'YYYY-MM-DD' format.")
        raise ValueError("PurchaseDate must be a date or 'YYYY-MM-DD' string.")

    # ------------------------------------------------------------------ #
    # Convenience helpers
    # ------------------------------------------------------------------ #
    def is_available(self):
        """True if this book is free to be issued."""
        return self.status == self.AVAILABLE

    def to_dict(self):
        """Return the book's data as a plain dict (handy for the UI/tables)."""
        return {
            "BookID": self.book_id,
            "Title": self.title,
            "Author": self.author,
            "Category": self.category,
            "PurchaseDate": self.purchase_date,
            "Status": self.status,
            "Remarks": self.remarks,
        }

    # ------------------------------------------------------------------ #
    # String representations
    # ------------------------------------------------------------------ #
    def __str__(self):
        """Friendly, human-readable summary (for UI messages / printing)."""
        author = self.author if self.author else "Unknown author"
        return f"'{self.title}' by {author} [{self.status}]"

    def __repr__(self):
        """Unambiguous developer view (for debugging / logs)."""
        return (
            f"Book(book_id={self.book_id!r}, title={self.title!r}, "
            f"author={self.author!r}, category={self.category!r}, "
            f"status={self.status!r})"
        )
