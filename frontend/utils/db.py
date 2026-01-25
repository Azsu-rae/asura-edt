"""Database connection utilities."""

import os
import sys
import time
import mysql.connector
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))


def get_connection():
    """Create and return a database connection."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
    )


def execute_with_timing(query, params=None):
    """Execute a query and return results with execution time."""
    conn = get_connection()
    cur = conn.cursor()

    start_time = time.time()
    cur.execute(query, params or ())
    results = cur.fetchall()
    elapsed = time.time() - start_time

    columns = [desc[0] for desc in cur.description] if cur.description else []

    conn.close()

    return results, columns, elapsed
