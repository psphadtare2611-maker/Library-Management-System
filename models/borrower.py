# ============================================================================
# models/borrower.py
# ----------------------------------------------------------------------------
# BORROWER ENTITY — an object-oriented representation of a friend who borrows
# books from the home library.
#
# Fields (user-facing): Name (required), Phone, Email, Address.
#   - borrower_id is NOT something you type in. Like BookID, it is assigned
#     automatically by the database (IDENTITY primary key) and used internally
#     so transactions can point at the correct borrower. It defaults to None
#     for a brand-new borrower that has not been saved yet.
#
# This class holds data and validates it. It contains NO SQL — persistence is
# the service/repository's job.
# ============================================================================

import re


class Borrower:
    """A single person who can borrow books from the library."""

    # Basic email shape: something@something.something
    _EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __init__(
        self,
        name,
        phone=None,
        email=None,
        address=None,
        borrower_id=None,      # internal DB id; None until saved
    ):
        """
        Create a Borrower.

        name        : required — the person's name.
        phone       : optional — contact number.
        email       : optional — email address (validated if provided).
        address     : optional — postal address / note on where they live.
        borrower_id : set by the database; leave None when creating new.
        """
        self.borrower_id = borrower_id
        self.name = name.strip() if isinstance(name, str) else name
        self.phone = phone.strip() if isinstance(phone, str) else phone
        self.email = email.strip() if isinstance(email, str) else email
        self.address = address.strip() if isinstance(address, str) else address

        # Validate immediately so an invalid Borrower can never exist.
        self.validate()

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    def validate(self):
        """
        Check the borrower's data. Raises ValueError with a clear message on
        the first problem found. Called automatically on creation.
        """
        # Name is the only required field.
        if not self.name or not str(self.name).strip():
            raise ValueError("Borrower name is required and cannot be empty.")

        # Phone (optional): if given, must contain 7–15 digits and only
        # sensible characters (digits, spaces, +, -, parentheses).
        if self.phone:
            digits = re.sub(r"\D", "", self.phone)   # keep only the digits
            if not re.fullmatch(r"[0-9+\-() ]+", self.phone):
                raise ValueError("Phone may only contain digits, spaces, +, -, ( and ).")
            if not (7 <= len(digits) <= 15):
                raise ValueError("Phone must contain between 7 and 15 digits.")

        # Email (optional): if given, must look like a valid address.
        if self.email and not self._EMAIL_PATTERN.match(self.email):
            raise ValueError("Email is not a valid address (expected name@domain.com).")

        return True

    # ------------------------------------------------------------------ #
    # Convenience helpers
    # ------------------------------------------------------------------ #
    def to_dict(self):
        """Return the borrower's data as a plain dict (handy for UI tables)."""
        return {
            "BorrowerID": self.borrower_id,
            "Name": self.name,
            "Phone": self.phone,
            "Email": self.email,
            "Address": self.address,
        }

    # ------------------------------------------------------------------ #
    # String representations
    # ------------------------------------------------------------------ #
    def __str__(self):
        """Friendly, human-readable summary (for UI messages / printing)."""
        contact = self.phone or self.email or "no contact info"
        return f"{self.name} ({contact})"

    def __repr__(self):
        """Unambiguous developer view (for debugging / logs)."""
        return (
            f"Borrower(borrower_id={self.borrower_id!r}, name={self.name!r}, "
            f"phone={self.phone!r}, email={self.email!r})"
        )
