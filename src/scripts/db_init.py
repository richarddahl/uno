# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
# uno framework
"""
PostgreSQL database initialization script.

This script is designed to run when a PostgreSQL container starts up.
It ensures all required extensions are enabled in the database.
"""

import argparse
import os

# SPDX-FileCopyrightText: 2024-present Richard Dahl <richard@dahl.us>
# SPDX-License-Identifier: MIT
import sys

from uno.core.logging.logger import LoggerService


def init_database(
    db_user: str = None,
    db_name: str = None,
    extensions: list[str] | None = None,
    graph_name: str = "graph",
    logger_service: LoggerService | None = None,
) -> int:
    """
    Initialize the PostgreSQL database with required extensions.

    Args:
        db_user: Database username (defaults to POSTGRES_USER env var)
        db_name: Database name (defaults to POSTGRES_DB env var)
        extensions: List of extensions to enable
        graph_name: Name for the Age graph
        logger_service: DI logger service

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    logger = (logger_service or LoggerService()).get_logger("db_init")

    # Get username and database name from environment if not provided
    if db_user is None:
        db_user = os.environ.get("POSTGRES_USER", "postgres")

    if db_name is None:
        db_name = os.environ.get("POSTGRES_DB", "postgres")

    # Default extensions to enable
    if extensions is None:
        extensions = [
            "btree_gist",
            "hstore",
            "pgcrypto",
            "pgjwt",
            "supa_audit CASCADE",
            "vector",
            "age",
        ]

    # Build SQL statements for extensions
    extension_statements = []
    for ext in extensions:
        extension_statements.append(f"CREATE EXTENSION IF NOT EXISTS {ext};")

    # Add Age graph setup if 'age' is in extensions
    if "age" in extensions:
        extension_statements.append(
            f"SELECT * FROM ag_catalog.create_graph('{graph_name}');"
        )

    # Combine all SQL statements
    sql = "\n".join(["-- Enable extensions"] + extension_statements)

    # Create a temporary SQL file
    with open("/tmp/init_extensions.sql", "w") as f:
        f.write(sql)

    try:
        # Run psql command to execute the SQL
        import subprocess

        cmd = [
            "psql",
            "-v",
            "ON_ERROR_STOP=1",
            "--username",
            db_user,
            "--dbname",
            db_name,
            "-f",
            "/tmp/init_extensions.sql",
        ]

        logger.info(f"Initializing PostgreSQL with extensions: {', '.join(extensions)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode != 0:
            logger.error(f"Error initializing database: {result.stderr}")
            return result.returncode

        logger.info("Database initialization completed successfully")
        return 0
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return 1
    finally:
        # Clean up temporary file
        try:
            os.remove("/tmp/init_extensions.sql")
        except:
            pass


def main() -> int:
    """
    Main entry point for the database initialization script.

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(
        description="Initialize PostgreSQL database with extensions"
    )
    parser.add_argument(
        "--db-user", help="Database username (defaults to POSTGRES_USER env var)"
    )
    parser.add_argument(
        "--db-name", help="Database name (defaults to POSTGRES_DB env var)"
    )
    parser.add_argument(
        "--extension",
        action="append",
        help="Extension to enable (can be specified multiple times)",
    )
    parser.add_argument(
        "--graph-name", default="graph", help="Name for the Age graph (default: graph)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    logger_service = LoggerService()
    return init_database(
        db_user=args.db_user,
        db_name=args.db_name,
        extensions=args.extension,
        graph_name=args.graph_name,
        logger_service=logger_service,
    )


if __name__ == "__main__":
    sys.exit(main())
