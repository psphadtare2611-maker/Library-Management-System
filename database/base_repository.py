# ============================================================================
# database/base_repository.py
# ----------------------------------------------------------------------------
# BASE REPOSITORY — shared foundation for all repository classes.
#
# Responsibilities (to be implemented later):
#   - Hold a reference to the DatabaseConnection
#   - Provide common query helpers used by every repository:
#         execute()       -> run INSERT/UPDATE/DELETE statements
#         fetch_one()     -> return a single row
#         fetch_all()     -> return multiple rows
#   - Handle parameterized queries (prevents SQL injection)
#
# Concrete repositories (Book, Borrower, Transaction) inherit from this
# to avoid repeating boilerplate SQL-execution code.
# ============================================================================
