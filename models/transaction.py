# ============================================================================
# models/transaction.py
# ----------------------------------------------------------------------------
# TRANSACTION ENTITY — one borrowing record (the core record of the system).
#
# Fields:
#   transaction_id       - hidden DB-assigned id (None until saved)
#   book_id              - which book (internal id)
#   borrower_id          - who borrowed it (internal id)
#   issue_date           - when it went out (defaults to today)
#   expected_return_date - the due date
#   return_date          - when it came back; None means STILL OUT
#   status               - 'Issued' / 'Returned' / 'Overdue'
#   remarks              - optional notes
#
# This class holds data and validates it. It contains NO SQL — persistence is
# the CirculationService's job.
# ============================================================================

from datetime import date, datetime


class Transaction:
    """A single issue/return record for one book and one borrower."""

    VALID_STATUSES = ("Issued", "Returned", "Overdue")

    def __init__(
        self,
        book_id,
        borrower_id,
        expected_return_date,
        issue_date=None,          # defaults to today if not given
        return_date=None,
        status="Issued",
        remarks=None,
        transaction_id=None,
    ):
        self.transaction_id = transaction_id
        self.book_id = book_id
        self.borrower_id = borrower_id
        self.issue_date = self._coerce_date(issue_date) or date.today()
        self.expected_return_date = self._coerce_date(expected_return_date)
        self.return_date = self._coerce_date(return_date)
        self.status = status
        self.remarks = remarks.strip() if isinstance(remarks, str) else remarks

        self.validate()

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def validate(self):
        """Check the record makes sense. Raises ValueError on the first issue."""
        if self.book_id is None:
            raise ValueError("A transaction must reference a book.")
        if self.borrower_id is None:
            raise ValueError("A transaction must reference a borrower.")

        if self.status not in self.VALID_STATUSES:
            raise ValueError(
                f"Invalid status '{self.status}'. "
                f"Must be one of: {', '.join(self.VALID_STATUSES)}."
            )

        if self.expected_return_date is None:
            raise ValueError("An expected return date is required.")

        # The due date cannot be before the issue date.
        if self.expected_return_date < self.issue_date:
            raise ValueError("Expected return date cannot be before the issue date.")

        # If returned, the return date cannot be before the issue date.
        if self.return_date is not None and self.return_date < self.issue_date:
            raise ValueError("Return date cannot be before the issue date.")

        return True

    @staticmethod
    def _coerce_date(value):
        """Accept a date or 'YYYY-MM-DD' string; None stays None."""
        if value is None or isinstance(value, date):
            return value
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Dates must be in 'YYYY-MM-DD' format.")
        raise ValueError("Dates must be a date or 'YYYY-MM-DD' string.")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def is_returned(self):
        """True once the book has been returned."""
        return self.return_date is not None

    def to_dict(self):
        return {
            "TransactionID": self.transaction_id,
            "BookID": self.book_id,
            "BorrowerID": self.borrower_id,
            "IssueDate": self.issue_date,
            "ExpectedReturnDate": self.expected_return_date,
            "ReturnDate": self.return_date,
            "Status": self.status,
            "Remarks": self.remarks,
        }

    # ------------------------------------------------------------------ #
    # String representations
    # ------------------------------------------------------------------ #
    def __str__(self):
        state = "returned" if self.is_returned() else "out"
        return (f"Transaction #{self.transaction_id} "
                f"(book {self.book_id} -> borrower {self.borrower_id}, {state})")

    def __repr__(self):
        return (
            f"Transaction(transaction_id={self.transaction_id!r}, "
            f"book_id={self.book_id!r}, borrower_id={self.borrower_id!r}, "
            f"status={self.status!r}, return_date={self.return_date!r})"
        )
