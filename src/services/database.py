"""
Optimized database service with connection pooling and query optimization
"""

import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
from queue import Queue, Empty
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabasePool:
    """SQLite connection pool for improved performance"""
    
    def __init__(self, database_path: str, pool_size: int = 10, timeout: float = 30.0):
        self.database_path = database_path
        self.pool_size = pool_size
        self.timeout = timeout
        self.pool = Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        self.stats = {
            "connections_created": 0,
            "connections_reused": 0,
            "active_connections": 0,
            "pool_hits": 0,
            "pool_misses": 0
        }
        
        # Pre-populate pool
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize the connection pool"""
        for _ in range(self.pool_size):
            conn = self._create_connection()
            if conn:
                self.pool.put(conn)
    
    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """Create a new database connection with optimizations"""
        try:
            conn = sqlite3.connect(
                self.database_path,
                timeout=self.timeout,
                check_same_thread=False
            )
            
            # Enable optimizations
            conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            conn.execute("PRAGMA synchronous=NORMAL")  # Balance safety/performance
            conn.execute("PRAGMA cache_size=10000")  # 10MB cache
            conn.execute("PRAGMA temp_store=MEMORY")  # Use memory for temp tables
            conn.execute("PRAGMA mmap_size=268435456")  # 256MB memory map
            conn.execute("PRAGMA foreign_keys=ON")  # Enable foreign keys
            
            # Set row factory for better data access
            conn.row_factory = sqlite3.Row
            
            with self.lock:
                self.stats["connections_created"] += 1
            
            return conn
        except sqlite3.Error as e:
            logger.error(f"Failed to create database connection: {e}")
            return None
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = None
        try:
            # Try to get from pool
            try:
                conn = self.pool.get_nowait()
                with self.lock:
                    self.stats["pool_hits"] += 1
                    self.stats["connections_reused"] += 1
            except Empty:
                # Pool empty, create new connection
                conn = self._create_connection()
                with self.lock:
                    self.stats["pool_misses"] += 1
            
            if conn is None:
                raise sqlite3.Error("Could not obtain database connection")
            
            with self.lock:
                self.stats["active_connections"] += 1
            
            yield conn
            
        finally:
            if conn:
                with self.lock:
                    self.stats["active_connections"] -= 1
                
                # Return to pool if space available
                try:
                    self.pool.put_nowait(conn)
                except:
                    # Pool full, close connection
                    conn.close()
    
    def close_all(self):
        """Close all connections in the pool"""
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except Empty:
                break
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        with self.lock:
            return self.stats.copy()

class OptimizedDatabase:
    """Optimized database service with indexing and query optimization"""
    
    def __init__(self, database_path: str):
        self.pool = DatabasePool(database_path)
        self.query_cache = {}
        self.query_stats = {}
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for better query performance"""
        indexes = [
            # Costs table indexes
            "CREATE INDEX IF NOT EXISTS idx_costs_date ON costs(date)",
            "CREATE INDEX IF NOT EXISTS idx_costs_category ON costs(category)",
            "CREATE INDEX IF NOT EXISTS idx_costs_amount ON costs(amount)",
            "CREATE INDEX IF NOT EXISTS idx_costs_date_category ON costs(date, category)",
            
            # Sales orders indexes
            "CREATE INDEX IF NOT EXISTS idx_sales_date ON sales_orders(date)",
            "CREATE INDEX IF NOT EXISTS idx_sales_status ON sales_orders(status)",
            "CREATE INDEX IF NOT EXISTS idx_sales_customer ON sales_orders(customer)",
            "CREATE INDEX IF NOT EXISTS idx_sales_date_status ON sales_orders(date, status)",
            
            # Payment schedule indexes
            "CREATE INDEX IF NOT EXISTS idx_payment_due_date ON payment_schedule(due_date)",
            "CREATE INDEX IF NOT EXISTS idx_payment_status ON payment_schedule(status)",
            "CREATE INDEX IF NOT EXISTS idx_payment_category ON payment_schedule(category)",
            
            # FX rates indexes
            "CREATE INDEX IF NOT EXISTS idx_fx_date ON fx_rates(date)",
            "CREATE INDEX IF NOT EXISTS idx_fx_currency ON fx_rates(currency_pair)",
            
            # Loan payments indexes
            "CREATE INDEX IF NOT EXISTS idx_loan_date ON loan_payments(payment_date)",
            "CREATE INDEX IF NOT EXISTS idx_loan_status ON loan_payments(status)"
        ]
        
        with self.pool.get_connection() as conn:
            for index_sql in indexes:
                try:
                    conn.execute(index_sql)
                    logger.debug(f"Created index: {index_sql}")
                except sqlite3.Error as e:
                    logger.warning(f"Failed to create index: {e}")
            conn.commit()
    
    def execute_query(self, query: str, params: Tuple = (), fetch: str = "all") -> Any:
        """Execute optimized query with statistics tracking"""
        start_time = time.time()
        
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                
                if fetch == "all":
                    result = cursor.fetchall()
                elif fetch == "one":
                    result = cursor.fetchone()
                elif fetch == "many":
                    result = cursor.fetchmany()
                else:
                    result = cursor.rowcount
                
                # Track query statistics
                execution_time = time.time() - start_time
                query_hash = hash(query)
                
                if query_hash not in self.query_stats:
                    self.query_stats[query_hash] = {
                        "query": query[:100] + "..." if len(query) > 100 else query,
                        "count": 0,
                        "total_time": 0,
                        "avg_time": 0,
                        "max_time": 0
                    }
                
                stats = self.query_stats[query_hash]
                stats["count"] += 1
                stats["total_time"] += execution_time
                stats["avg_time"] = stats["total_time"] / stats["count"]
                stats["max_time"] = max(stats["max_time"], execution_time)
                
                return result
                
        except sqlite3.Error as e:
            logger.error(f"Database query failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise
    
    def execute_transaction(self, queries: List[Tuple[str, Tuple]]) -> bool:
        """Execute multiple queries in a transaction"""
        try:
            with self.pool.get_connection() as conn:
                conn.execute("BEGIN TRANSACTION")
                
                for query, params in queries:
                    conn.execute(query, params)
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Transaction failed: {e}")
            conn.rollback()
            return False
    
    def get_dataframe(self, query: str, params: Tuple = ()) -> pd.DataFrame:
        """Execute query and return pandas DataFrame"""
        try:
            with self.pool.get_connection() as conn:
                df = pd.read_sql_query(query, conn, params=params)
                return df
        except Exception as e:
            logger.error(f"DataFrame query failed: {e}")
            return pd.DataFrame()
    
    def bulk_insert(self, table: str, data: List[Dict[str, Any]]) -> bool:
        """Optimized bulk insert operation"""
        if not data:
            return True
        
        # Prepare bulk insert query
        columns = list(data[0].keys())
        placeholders = ", ".join(["?" for _ in columns])
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        
        # Convert data to tuples
        values = [tuple(row[col] for col in columns) for row in data]
        
        try:
            with self.pool.get_connection() as conn:
                conn.executemany(query, values)
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Bulk insert failed: {e}")
            return False
    
    def analyze_tables(self) -> Dict[str, Any]:
        """Analyze table statistics for optimization"""
        analysis = {}
        
        tables = ["costs", "sales_orders", "payment_schedule", "fx_rates", "loan_payments"]
        
        for table in tables:
            try:
                # Get row count
                row_count = self.execute_query(f"SELECT COUNT(*) FROM {table}", fetch="one")[0]
                
                # Get table info
                table_info = self.execute_query(f"PRAGMA table_info({table})")
                
                # Get index info
                index_info = self.execute_query(f"PRAGMA index_list({table})")
                
                analysis[table] = {
                    "row_count": row_count,
                    "columns": len(table_info),
                    "indexes": len(index_info),
                    "table_info": [dict(row) for row in table_info],
                    "index_info": [dict(row) for row in index_info]
                }
                
            except sqlite3.Error as e:
                logger.error(f"Failed to analyze table {table}: {e}")
                analysis[table] = {"error": str(e)}
        
        return analysis
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slowest queries for optimization"""
        sorted_queries = sorted(
            self.query_stats.values(),
            key=lambda x: x["avg_time"],
            reverse=True
        )
        return sorted_queries[:limit]
    
    def vacuum_database(self) -> bool:
        """Vacuum database to reclaim space and optimize"""
        try:
            with self.pool.get_connection() as conn:
                conn.execute("VACUUM")
                conn.commit()
                logger.info("Database vacuum completed")
                return True
        except sqlite3.Error as e:
            logger.error(f"Database vacuum failed: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        stats = {
            "pool_stats": self.pool.get_stats(),
            "query_count": len(self.query_stats),
            "total_queries_executed": sum(q["count"] for q in self.query_stats.values()),
            "avg_query_time": (
                sum(q["avg_time"] for q in self.query_stats.values()) / len(self.query_stats)
                if self.query_stats else 0
            )
        }
        
        # Add database size info
        try:
            with self.pool.get_connection() as conn:
                result = conn.execute("PRAGMA page_count").fetchone()
                page_count = result[0] if result else 0
                
                result = conn.execute("PRAGMA page_size").fetchone()
                page_size = result[0] if result else 0
                
                stats["database_size_bytes"] = page_count * page_size
                stats["database_size_mb"] = (page_count * page_size) / (1024 * 1024)
                
        except sqlite3.Error as e:
            logger.error(f"Failed to get database size: {e}")
        
        return stats
    
    def close(self):
        """Close database pool"""
        self.pool.close_all()

# Global database instance
db_service = None

def get_database_service(database_path: str = "cashflow.db") -> OptimizedDatabase:
    """Get or create database service instance"""
    global db_service
    if db_service is None:
        db_service = OptimizedDatabase(database_path)
    return db_service
