"""Verify the local PostgreSQL connection and required project tables.

The connection uses PostgreSQL's standard PGHOST, PGPORT, PGDATABASE,
PGUSER, and PGPASSWORD environment variables. This script is read-only.
"""

from __future__ import annotations

import sys

import psycopg
from psycopg import OperationalError


EXPECTED_TABLES = {
    "processing_runs",
    "input_files",
    "leads",
    "lead_occurrences",
    "qualification_results",
    "outreach_drafts",
    "review_events",
}


def check_database() -> dict[str, object]:
    """Return database identity and schema status using read-only queries."""

    with psycopg.connect() as connection:
        connection.read_only = True

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    current_database(),
                    current_user,
                    current_schema(),
                    version()
                """
            )
            database, user, schema, version = cursor.fetchone()

            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            tables = {row[0] for row in cursor.fetchall()}

    return {
        "database": database,
        "user": user,
        "schema": schema,
        "version": version.split(",")[0],
        "tables": sorted(tables),
        "missing_tables": sorted(EXPECTED_TABLES - tables),
    }


def main() -> int:
    """Run the connection check and print a password-free result."""

    try:
        result = check_database()
    except OperationalError as error:
        print("Database connection failed.")
        print(str(error).strip())
        print(
            "Check PGHOST, PGPORT, PGDATABASE, PGUSER, and PGPASSWORD "
            "in this PowerShell session."
        )
        return 1

    print(f"Connected database: {result['database']}")
    print(f"Connected user: {result['user']}")
    print(f"Current schema: {result['schema']}")
    print(f"PostgreSQL version: {result['version']}")
    print(f"Required tables found: {len(EXPECTED_TABLES) - len(result['missing_tables'])}/7")

    if result["missing_tables"]:
        print("Missing tables: " + ", ".join(result["missing_tables"]))
        return 1

    print("Schema check passed: all seven required tables are present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
