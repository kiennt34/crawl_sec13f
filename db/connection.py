"""
MariaDB connection management.
"""
import pymysql
from typing import Optional
from contextlib import contextmanager
from config import Config


class DatabaseConnection:
    """Manages MariaDB connections."""
    
    def __init__(self):
        self.conn: Optional[pymysql.Connection] = None
    
    def connect(self) -> pymysql.Connection:
        """Create and return a database connection."""
        if self.conn is None or not self.conn.open:
            self.conn = pymysql.connect(**Config.get_db_connection_string())
        return self.conn
    
    def close(self) -> None:
        """Close the database connection."""
        if self.conn and self.conn.open:
            self.conn.close()
            self.conn = None
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = self.connect()
        try:
            yield conn
        finally:
            # Don't close here, let the connection be reused
            pass
    
    def __enter__(self):
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_db_connection() -> pymysql.Connection:
    """Get a database connection."""
    return pymysql.connect(**Config.get_db_connection_string())

