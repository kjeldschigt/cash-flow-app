"""
Base repository classes and database connection management.
"""

import sqlite3
import threading
import logging
from typing import Optional, Dict, Any, List, Union
from contextlib import contextmanager
from abc import ABC, abstractmethod
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from dataclasses import asdict
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DatabaseConnection:
    """Thread-safe database connection manager with connection pooling."""
    
    _instance = None
    _lock = threading.Lock()
    _connections = {}
    
    def __new__(cls, db_path: str = "cashflow.db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.db_path = db_path
        return cls._instance
    
    @staticmethod
    def _dict_factory(cursor, row):
        """Convert row to dictionary"""
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
    
    @contextmanager
    def get_connection(self):
        """Get a database connection for the current thread."""
        thread_id = threading.get_ident()
        
        if thread_id not in self._connections:
            self._connections[thread_id] = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            self._connections[thread_id].row_factory = self._dict_factory
            # Enable foreign keys
            self._connections[thread_id].execute("PRAGMA foreign_keys = ON")
        
        conn = self._connections[thread_id]
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.commit()
    
    def close_all_connections(self):
        """Close all database connections."""
        for conn in self._connections.values():
            conn.close()
        self._connections.clear()


class BaseRepository(ABC, Generic[T]):
    """Base repository class with common CRUD operations."""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self._table_name = self._get_table_name()
        self._model_class = self._get_model_class()
    
    @abstractmethod
    def _get_table_name(self) -> str:
        """Return the table name for this repository."""
        pass
    
    @abstractmethod
    def _get_model_class(self) -> Type[T]:
        """Return the model class for this repository."""
        pass
    
    @abstractmethod
    def _row_to_model(self, row: sqlite3.Row) -> T:
        """Convert database row to model instance."""
        pass
    
    @abstractmethod
    def _model_to_dict(self, model: T) -> Dict[str, Any]:
        """Convert model instance to dictionary for database storage."""
        pass
    
    def find_by_id(self, id: str) -> Optional[T]:
        """Find entity by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {self._table_name} WHERE id = ?", (id,))
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None
    
    def find_all(self, limit: Optional[int] = None, offset: int = 0) -> List[T]:
        """Find all entities with optional pagination."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            query = f"SELECT * FROM {self._table_name}"
            params = []
            
            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def save(self, model: T) -> T:
        """Save (insert or update) an entity."""
        data = self._model_to_dict(model)
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            if data.get('id'):
                # Update existing
                set_clause = ', '.join([f"{k} = ?" for k in data.keys() if k != 'id'])
                values = [v for k, v in data.items() if k != 'id']
                values.append(data['id'])
                
                cursor.execute(
                    f"UPDATE {self._table_name} SET {set_clause} WHERE id = ?",
                    values
                )
            else:
                # Insert new
                import uuid
                data['id'] = str(uuid.uuid4())
                
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?' for _ in data])
                values = list(data.values())
                
                cursor.execute(
                    f"INSERT INTO {self._table_name} ({columns}) VALUES ({placeholders})",
                    values
                )
            
            # Return updated model with ID
            return self.find_by_id(data['id'])
    
    def get_cursor(self) -> sqlite3.Cursor:
        """Get database cursor with row factory"""
        conn = self.db.get_connection()
        conn.row_factory = self._dict_factory
        return conn.cursor()
    
    @staticmethod
    def _dict_factory(cursor, row):
        """Convert row to dictionary"""
        return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}
    
    def delete(self, id: str) -> bool:
        """Delete entity by ID."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {self._table_name} WHERE id = ?", (id,))
            return cursor.rowcount > 0
    
    def count(self) -> int:
        """Count total entities."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {self._table_name}")
            return cursor.fetchone()[0]
    
    def execute_query(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        """Execute custom query and return rows."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
