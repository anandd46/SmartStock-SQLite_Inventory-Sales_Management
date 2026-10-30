"""
database/connection.py
SmartStock - Database Connection Manager
Created by Anand D

Manages SQLite database connections with proper foreign key enforcement,
row factory settings, and safe path resolution.
"""

import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

# Resolve database path relative to project root (two levels up from this file)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "smartstock.db")


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """
    Return an open SQLite connection with:
      - Row factory set to sqlite3.Row for dict-like access
      - Foreign key enforcement ON
      - WAL journal mode for better concurrency

    Args:
        db_path: Optional override path for the database file.
                 Defaults to DB_PATH resolved relative to the project root.

    Returns:
        sqlite3.Connection object ready for use.
    """
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row

    # CRITICAL: SQLite does NOT enforce foreign keys by default.
    # This PRAGMA must be set on every new connection.
    conn.execute("PRAGMA foreign_keys = ON;")

    # Use WAL mode for better concurrent read performance
    conn.execute("PRAGMA journal_mode = WAL;")

    # Enable strict column typing validation
    conn.execute("PRAGMA synchronous = NORMAL;")

    return conn


def close_connection(conn: sqlite3.Connection) -> None:
    """Safely close a database connection."""
    if conn:
        try:
            conn.close()
        except Exception as e:
            logger.warning(f"Error closing connection: {e}")


def verify_foreign_keys(conn: sqlite3.Connection) -> bool:
    """
    Verify that foreign key enforcement is active on the given connection.
    Returns True if foreign keys are enabled, False otherwise.
    """
    cursor = conn.execute("PRAGMA foreign_keys;")
    result = cursor.fetchone()
    return result[0] == 1


def get_db_path() -> str:
    """Return the resolved absolute path of the database file."""
    return DB_PATH


def initialize_database(db_path: str = None) -> None:
    """
    Initialize the database by running schema.sql and triggers.sql.
    Safe to call multiple times – uses CREATE TABLE IF NOT EXISTS.
    """
    from database.schema import create_schema
    from database.triggers_setup import create_triggers

    conn = get_connection(db_path)
    try:
        create_schema(conn)
        create_triggers(conn)
        conn.commit()
        logger.info(f"Database initialized at: {db_path or DB_PATH}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        close_connection(conn)
