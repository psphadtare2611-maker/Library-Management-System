# ============================================================================
# config/settings.py
# ----------------------------------------------------------------------------
# CENTRAL CONFIGURATION for the whole application.
#
# Everything that might need tweaking lives here — so there are no "magic
# numbers" or hard-coded connection strings scattered through the code.
#
# NOTE: for a real deployment, keep credentials out of version control by
#       putting them in config/secrets.py (git-ignored) and importing here.
# ============================================================================


# ----------------------------------------------------------------------------
# DATABASE CONNECTION SETTINGS (SQL Server)
# ----------------------------------------------------------------------------
# Adjust these to match your local SQL Server instance.
#
#   DRIVER   - the installed ODBC driver. "ODBC Driver 17 for SQL Server" is
#              the common one; older machines may have "SQL Server".
#   SERVER   - your SQL Server instance name. Examples:
#                 "localhost"                (default instance)
#                 "localhost\\SQLEXPRESS"    (SQL Server Express)
#                 ".\\SQLEXPRESS"
#   DATABASE - the database created by database/schema.sql
#   TRUSTED_CONNECTION - "yes" uses Windows authentication (no user/password).
#                        Set to "no" and fill USERNAME/PASSWORD for SQL auth.
# ----------------------------------------------------------------------------
DB_CONFIG = {
    "DRIVER": "ODBC Driver 17 for SQL Server",
    "SERVER": "localhost\\SQLEXPRESS",
    "DATABASE": "LibraryDB",
    "TRUSTED_CONNECTION": "yes",   # Windows authentication
    "USERNAME": "",                # used only when TRUSTED_CONNECTION = "no"
    "PASSWORD": "",                # used only when TRUSTED_CONNECTION = "no"
}


def get_connection_string() -> str:
    """
    Build the pyodbc connection string from DB_CONFIG.

    Keeping this in one function means the connection module never has to
    know HOW the string is assembled — it just asks for the finished string.
    """
    if DB_CONFIG["TRUSTED_CONNECTION"].lower() == "yes":
        # Windows authentication — no username/password needed.
        return (
            f"DRIVER={{{DB_CONFIG['DRIVER']}}};"
            f"SERVER={DB_CONFIG['SERVER']};"
            f"DATABASE={DB_CONFIG['DATABASE']};"
            f"Trusted_Connection=yes;"
        )

    # SQL Server authentication — username/password.
    return (
        f"DRIVER={{{DB_CONFIG['DRIVER']}}};"
        f"SERVER={DB_CONFIG['SERVER']};"
        f"DATABASE={DB_CONFIG['DATABASE']};"
        f"UID={DB_CONFIG['USERNAME']};"
        f"PWD={DB_CONFIG['PASSWORD']};"
    )


# ----------------------------------------------------------------------------
# BUSINESS CONSTANTS
# ----------------------------------------------------------------------------
LOAN_PERIOD_DAYS = 14          # default borrowing window (used to set due date)

# ----------------------------------------------------------------------------
# APPLICATION METADATA
# ----------------------------------------------------------------------------
APP_NAME = "Library Management System"
WINDOW_SIZE = "1000x650"
