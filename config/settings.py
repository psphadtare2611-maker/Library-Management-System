# ============================================================================
# config/settings.py
# ----------------------------------------------------------------------------
# CENTRAL CONFIGURATION for the whole application.
#
# Everything that might need tweaking lives here — so there are no "magic
# numbers" or hard-coded connection strings scattered through the code.
#
# Will hold (to be implemented later):
#   - SQL Server connection details (server, database, driver, auth)
#   - Business constants:
#         LOAN_PERIOD_DAYS   -> how long a book can be borrowed (e.g. 14)
#         FINE_PER_DAY       -> optional overdue fine rate
#   - Application metadata (app name, window size, theme colors)
#
# NOTE: real credentials should be kept out of version control.
#       Put secrets in config/secrets.py (git-ignored) and import them here.
# ============================================================================
