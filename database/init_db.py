# ============================================================================
# database/init_db.py
# ----------------------------------------------------------------------------
# DATABASE INITIALIZER — creates (or resets) LibraryDB from schema.sql.
#
# Why this exists:
#   schema.sql uses 'GO' batch separators and a CREATE DATABASE statement.
#   'GO' is an SSMS/sqlcmd feature (not real T-SQL), and CREATE DATABASE
#   cannot run inside a transaction. So we cannot just hand the whole file to
#   pyodbc. This script:
#       1. Connects to the 'master' database (not LibraryDB, which may not
#          exist yet) using the server/driver/auth from config/settings.py.
#       2. Splits schema.sql into batches on the 'GO' lines.
#       3. Runs each batch with autocommit on.
#
# Usage:
#   python -m database.init_db
#
# NOTE: schema.sql DROPs and recreates the tables, so running this wipes any
# existing data in LibraryDB. That is intended for setup/development.
# ============================================================================

import os
import re

import pyodbc

from config.settings import DB_CONFIG


def _master_connection_string():
    """Build a connection string that points at 'master' (always exists)."""
    if DB_CONFIG["TRUSTED_CONNECTION"].lower() == "yes":
        return (
            f"DRIVER={{{DB_CONFIG['DRIVER']}}};"
            f"SERVER={DB_CONFIG['SERVER']};"
            f"DATABASE=master;"
            f"Trusted_Connection=yes;"
        )
    return (
        f"DRIVER={{{DB_CONFIG['DRIVER']}}};"
        f"SERVER={DB_CONFIG['SERVER']};"
        f"DATABASE=master;"
        f"UID={DB_CONFIG['USERNAME']};"
        f"PWD={DB_CONFIG['PASSWORD']};"
    )


def _read_batches(sql_path):
    """Read schema.sql and split it into batches on standalone 'GO' lines."""
    with open(sql_path, "r", encoding="utf-8") as handle:
        script = handle.read()
    # Split on a line that is just 'GO' (case-insensitive), ignoring surrounding
    # whitespace. Keep only batches that contain actual statements.
    parts = re.split(r"(?im)^\s*GO\s*$", script)
    return [p.strip() for p in parts if p.strip()]


def initialize():
    """Run schema.sql against the configured SQL Server instance."""
    sql_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    batches = _read_batches(sql_path)

    print(f"Connecting to {DB_CONFIG['SERVER']} (master) ...")
    connection = pyodbc.connect(_master_connection_string(), autocommit=True)
    cursor = connection.cursor()

    try:
        for index, batch in enumerate(batches, start=1):
            cursor.execute(batch)
        print(f"Executed {len(batches)} batch(es). LibraryDB is ready.")
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    try:
        initialize()
        print("Database initialization complete.")
    except Exception as error:
        print(f"Initialization FAILED: {error}")
        raise
