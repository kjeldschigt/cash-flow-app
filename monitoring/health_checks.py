"""
Health Checks and System Monitoring
"""

import sqlite3
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import streamlit as st
from pathlib import Path

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class HealthCheckResult:
    name: str
    status: HealthStatus
    message: str
    response_time_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class DatabaseHealthChecker:
    """Database connectivity and integrity checks"""
    
    def __init__(self, db_path: str = "cashflow.db", users_db_path: str = "users.db"):
        self.db_path = db_path
        self.users_db_path = users_db_path
    
    def check_connectivity(self) -> HealthCheckResult:
        """Check database connectivity"""
        start_time = time.time()
        
        try:
            # Test main database
            conn = sqlite3.connect(self.db_path, timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            
            # Test users database
            conn = sqlite3.connect(self.users_db_path, timeout=5.0)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            conn.close()
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name="database_connectivity",
                status=HealthStatus.HEALTHY,
                message="Database connections successful",
                response_time_ms=response_time
            )
            
        except sqlite3.Error as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheckResult(
                name="database_connectivity",
                status=HealthStatus.CRITICAL,
                message=f"Database connection failed: {str(e)}",
                response_time_ms=response_time,
                details={"error": str(e)}
            )
    
    def check_data_integrity(self) -> HealthCheckResult:
        """Check data integrity and consistency"""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            
            # Check for required tables
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['costs', 'sales_orders', 'cash_out', 'fx_rates']
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                conn.close()
                return HealthCheckResult(
                    name="data_integrity",
                    status=HealthStatus.CRITICAL,
                    message=f"Missing required tables: {missing_tables}",
                    details={"missing_tables": missing_tables}
                )
            
            # Check for data consistency
            integrity_issues = []
            
            # Check for negative amounts in costs
            cursor.execute("SELECT COUNT(*) FROM costs WHERE amount < 0")
            negative_costs = cursor.fetchone()[0]
            if negative_costs > 0:
                integrity_issues.append(f"{negative_costs} negative cost entries")
            
            # Check for future dates beyond reasonable range
            future_date = (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d')
            cursor.execute("SELECT COUNT(*) FROM costs WHERE date > ?", (future_date,))
            future_costs = cursor.fetchone()[0]
            if future_costs > 0:
                integrity_issues.append(f"{future_costs} costs with future dates")
            
            conn.close()
            
            if integrity_issues:
                return HealthCheckResult(
                    name="data_integrity",
                    status=HealthStatus.WARNING,
                    message=f"Data integrity issues found: {', '.join(integrity_issues)}",
                    details={"issues": integrity_issues}
                )
            
            return HealthCheckResult(
                name="data_integrity",
                status=HealthStatus.HEALTHY,
                message="Data integrity checks passed"
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="data_integrity",
                status=HealthStatus.CRITICAL,
                message=f"Data integrity check failed: {str(e)}",
                details={"error": str(e)}
            )

class ExternalAPIHealthChecker:
    """External API availability checks"""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def check_airtable_api(self, api_key: str = None, base_id: str = None) -> HealthCheckResult:
        """Check Airtable API availability"""
        if not api_key or not base_id:
            return HealthCheckResult(
                name="airtable_api",
                status=HealthStatus.WARNING,
                message="Airtable API credentials not configured"
            )
        
        start_time = time.time()
        
        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Test API with a simple request
            url = f"https://api.airtable.com/v0/{base_id}"
            response = requests.get(url, headers=headers, timeout=self.timeout)
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                return HealthCheckResult(
                    name="airtable_api",
                    status=HealthStatus.HEALTHY,
                    message="Airtable API accessible",
                    response_time_ms=response_time
                )
            elif response.status_code == 401:
                return HealthCheckResult(
                    name="airtable_api",
                    status=HealthStatus.CRITICAL,
                    message="Airtable API authentication failed",
                    response_time_ms=response_time,
                    details={"status_code": response.status_code}
                )
            else:
                return HealthCheckResult(
                    name="airtable_api",
                    status=HealthStatus.WARNING,
                    message=f"Airtable API returned status {response.status_code}",
                    response_time_ms=response_time,
                    details={"status_code": response.status_code}
                )
                
        except requests.exceptions.Timeout:
            return HealthCheckResult(
                name="airtable_api",
                status=HealthStatus.WARNING,
                message="Airtable API request timed out",
                response_time_ms=self.timeout * 1000
            )
        except requests.exceptions.ConnectionError:
            return HealthCheckResult(
                name="airtable_api",
                status=HealthStatus.CRITICAL,
                message="Cannot connect to Airtable API"
            )
        except Exception as e:
            return HealthCheckResult(
                name="airtable_api",
                status=HealthStatus.CRITICAL,
                message=f"Airtable API check failed: {str(e)}",
                details={"error": str(e)}
            )
    
    def check_stripe_api(self, api_key: str = None) -> HealthCheckResult:
        """Check Stripe API availability"""
        if not api_key:
            return HealthCheckResult(
                name="stripe_api",
                status=HealthStatus.WARNING,
                message="Stripe API key not configured"
            )
        
        start_time = time.time()
        
        try:
            import stripe
            stripe.api_key = api_key
            
            # Test API with account retrieval
            account = stripe.Account.retrieve()
            
            response_time = (time.time() - start_time) * 1000
            
            return HealthCheckResult(
                name="stripe_api",
                status=HealthStatus.HEALTHY,
                message="Stripe API accessible",
                response_time_ms=response_time,
                details={"account_id": account.id}
            )
            
        except stripe.error.AuthenticationError:
            return HealthCheckResult(
                name="stripe_api",
                status=HealthStatus.CRITICAL,
                message="Stripe API authentication failed"
            )
        except stripe.error.APIConnectionError:
            return HealthCheckResult(
                name="stripe_api",
                status=HealthStatus.CRITICAL,
                message="Cannot connect to Stripe API"
            )
        except ImportError:
            return HealthCheckResult(
                name="stripe_api",
                status=HealthStatus.WARNING,
                message="Stripe library not installed"
            )
        except Exception as e:
            return HealthCheckResult(
                name="stripe_api",
                status=HealthStatus.WARNING,
                message=f"Stripe API check failed: {str(e)}",
                details={"error": str(e)}
            )

class PerformanceBenchmarks:
    """Performance benchmarks and monitoring"""
    
    def __init__(self, db_path: str = "cashflow.db"):
        self.db_path = db_path
    
    def benchmark_database_queries(self) -> HealthCheckResult:
        """Benchmark common database queries"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            benchmarks = {}
            
            # Test queries with timing
            queries = {
                'simple_select': "SELECT COUNT(*) FROM costs",
                'complex_join': """
                    SELECT c.category, SUM(c.amount) as total
                    FROM costs c
                    GROUP BY c.category
                    ORDER BY total DESC
                """,
                'date_range_query': """
                    SELECT * FROM costs 
                    WHERE date >= date('now', '-30 days')
                """
            }
            
            for query_name, query in queries.items():
                start_time = time.time()
                cursor = conn.cursor()
                cursor.execute(query)
                cursor.fetchall()
                query_time = (time.time() - start_time) * 1000
                benchmarks[query_name] = query_time
            
            conn.close()
            
            # Determine status based on performance
            max_time = max(benchmarks.values())
            if max_time > 1000:  # > 1 second
                status = HealthStatus.WARNING
                message = f"Slow database queries detected (max: {max_time:.2f}ms)"
            elif max_time > 5000:  # > 5 seconds
                status = HealthStatus.CRITICAL
                message = f"Very slow database queries (max: {max_time:.2f}ms)"
            else:
                status = HealthStatus.HEALTHY
                message = f"Database queries performing well (max: {max_time:.2f}ms)"
            
            return HealthCheckResult(
                name="database_performance",
                status=status,
                message=message,
                details=benchmarks
            )
            
        except Exception as e:
            return HealthCheckResult(
                name="database_performance",
                status=HealthStatus.CRITICAL,
                message=f"Database benchmark failed: {str(e)}",
                details={"error": str(e)}
            )
    
    def check_memory_usage(self) -> HealthCheckResult:
        """Check application memory usage"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # Memory thresholds
            if memory_mb > 1000:  # > 1GB
                status = HealthStatus.CRITICAL
                message = f"High memory usage: {memory_mb:.2f}MB"
            elif memory_mb > 500:  # > 500MB
                status = HealthStatus.WARNING
                message = f"Elevated memory usage: {memory_mb:.2f}MB"
            else:
                status = HealthStatus.HEALTHY
                message = f"Memory usage normal: {memory_mb:.2f}MB"
            
            return HealthCheckResult(
                name="memory_usage",
                status=status,
                message=message,
                details={
                    "memory_mb": memory_mb,
                    "memory_percent": process.memory_percent()
                }
            )
            
        except ImportError:
            return HealthCheckResult(
                name="memory_usage",
                status=HealthStatus.WARNING,
                message="psutil not available for memory monitoring"
            )
        except Exception as e:
            return HealthCheckResult(
                name="memory_usage",
                status=HealthStatus.WARNING,
                message=f"Memory check failed: {str(e)}",
                details={"error": str(e)}
            )

class HealthCheckManager:
    """Main health check coordinator"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.db_checker = DatabaseHealthChecker()
        self.api_checker = ExternalAPIHealthChecker()
        self.perf_checker = PerformanceBenchmarks()
    
    def run_all_checks(self) -> List[HealthCheckResult]:
        """Run all health checks"""
        results = []
        
        # Database checks
        results.append(self.db_checker.check_connectivity())
        results.append(self.db_checker.check_data_integrity())
        
        # API checks
        airtable_key = self.config.get('airtable_api_key')
        airtable_base = self.config.get('airtable_base_id')
        results.append(self.api_checker.check_airtable_api(airtable_key, airtable_base))
        
        stripe_key = self.config.get('stripe_api_key')
        results.append(self.api_checker.check_stripe_api(stripe_key))
        
        # Performance checks
        results.append(self.perf_checker.benchmark_database_queries())
        results.append(self.perf_checker.check_memory_usage())
        
        return results
    
    def get_overall_status(self, results: List[HealthCheckResult]) -> HealthStatus:
        """Determine overall system status"""
        if any(r.status == HealthStatus.CRITICAL for r in results):
            return HealthStatus.CRITICAL
        elif any(r.status == HealthStatus.WARNING for r in results):
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def generate_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        results = self.run_all_checks()
        overall_status = self.get_overall_status(results)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'overall_status': overall_status.value,
            'checks': [
                {
                    'name': r.name,
                    'status': r.status.value,
                    'message': r.message,
                    'response_time_ms': r.response_time_ms,
                    'details': r.details
                }
                for r in results
            ],
            'summary': {
                'total_checks': len(results),
                'healthy': sum(1 for r in results if r.status == HealthStatus.HEALTHY),
                'warnings': sum(1 for r in results if r.status == HealthStatus.WARNING),
                'critical': sum(1 for r in results if r.status == HealthStatus.CRITICAL)
            }
        }

def create_health_endpoint():
    """Create Streamlit health check page"""
    st.title("🏥 System Health Dashboard")
    
    # Get configuration from session state or environment
    config = {
        'airtable_api_key': st.secrets.get('AIRTABLE_API_KEY'),
        'airtable_base_id': st.secrets.get('AIRTABLE_BASE_ID'),
        'stripe_api_key': st.secrets.get('STRIPE_API_KEY')
    }
    
    health_manager = HealthCheckManager(config)
    
    # Run health checks
    with st.spinner("Running health checks..."):
        report = health_manager.generate_health_report()
    
    # Display overall status
    overall_status = report['overall_status']
    if overall_status == 'healthy':
        st.success(f"🟢 System Status: {overall_status.upper()}")
    elif overall_status == 'warning':
        st.warning(f"🟡 System Status: {overall_status.upper()}")
    else:
        st.error(f"🔴 System Status: {overall_status.upper()}")
    
    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Checks", report['summary']['total_checks'])
    with col2:
        st.metric("Healthy", report['summary']['healthy'])
    with col3:
        st.metric("Warnings", report['summary']['warnings'])
    with col4:
        st.metric("Critical", report['summary']['critical'])
    
    # Display individual check results
    st.subheader("Individual Check Results")
    
    for check in report['checks']:
        with st.expander(f"{check['name']} - {check['status'].upper()}", expanded=check['status'] != 'healthy'):
            if check['status'] == 'healthy':
                st.success(check['message'])
            elif check['status'] == 'warning':
                st.warning(check['message'])
            else:
                st.error(check['message'])
            
            if check['response_time_ms']:
                st.info(f"Response time: {check['response_time_ms']:.2f}ms")
            
            if check['details']:
                st.json(check['details'])
    
    # Auto-refresh option
    if st.checkbox("Auto-refresh (30 seconds)"):
        time.sleep(30)
        st.rerun()

# Global health check manager
health_manager = HealthCheckManager()

def get_health_status() -> Dict[str, Any]:
    """Get current health status (for API endpoints)"""
    return health_manager.generate_health_report()
