# ============================================================================
# database/connection.py
# ----------------------------------------------------------------------------
# DATABASE CONNECTION MANAGER (SQL Server via pyodbc).
#
# Responsibilities (to be implemented later):
#   - Build the connection string from config/settings.py
#   - Open and close connections safely (context-manager / 'with' support)
#   - Provide a reusable cursor for repositories to execute queries
#   - Centralize connection error handling
#
# Every repository depends on this class. No other file should call pyodbc
# directly — this keeps connection logic in exactly one place.
# ============================================================================
