"""
Audit Logging for Financial Operations
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from ..repositories.base import DatabaseConnection
from .encryption import SecureStorage


class AuditAction(str, Enum):
    """Audit action types"""

    LOGIN = "login"
    LOGOUT = "logout"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    EXPORT = "export"
    PAYMENT_PROCESSED = "payment_processed"
    COST_ADDED = "cost_added"
    INTEGRATION_CONFIGURED = "integration_configured"


class AuditLevel(str, Enum):
    """Audit severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLogger:
    """Comprehensive audit logging for financial operations"""

    def __init__(
        self,
        db_connection: DatabaseConnection,
        secure_storage: Optional[SecureStorage] = None,
    ):
        self.db = db_connection
        self.secure_storage = secure_storage or SecureStorage()
        self.logger = logging.getLogger(__name__)

    def log_financial_operation(
        self,
        user_id: str,
        action: AuditAction,
        entity_type: str,
        entity_id: str,
        amount: Optional[float] = None,
        currency: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        level: AuditLevel = AuditLevel.INFO,
    ) -> None:
        """Log financial operations with enhanced security"""
        try:
            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "action": action.value,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "amount": amount,
                "currency": currency,
                "level": level.value,
                "details": details or {},
                "ip_address": self._get_client_ip(),
                "user_agent": self._get_user_agent(),
            }

            # Encrypt sensitive details
            if details and self._contains_sensitive_data(details):
                audit_entry["details"] = self.secure_storage.store_sensitive_data(
                    f"audit_{entity_id}_{datetime.now().timestamp()}", details
                )
                audit_entry["details_encrypted"] = True

            # Store in database
            self._store_audit_entry(audit_entry)

            # Log to application logger with PII masking
            masked_entry = self._mask_audit_entry(audit_entry)
            self.logger.info(f"Audit: {json.dumps(masked_entry, default=str)}")

        except Exception as e:
            self.logger.error(f"Failed to log audit entry: {str(e)}")

    def log_authentication_event(
        self,
        user_email: str,
        action: AuditAction,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log authentication events"""
        level = AuditLevel.INFO if success else AuditLevel.WARNING

        auth_details = {"success": success, "email": user_email, **(details or {})}

        self.log_financial_operation(
            user_id=user_email,
            action=action,
            entity_type="authentication",
            entity_id=f"auth_{datetime.now().timestamp()}",
            details=auth_details,
            level=level,
        )

    def log_data_access(
        self,
        user_id: str,
        resource: str,
        action: AuditAction = AuditAction.VIEW,
        filters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log data access events"""
        access_details = {
            "resource": resource,
            "filters": filters or {},
            "timestamp": datetime.now().isoformat(),
        }

        self.log_financial_operation(
            user_id=user_id,
            action=action,
            entity_type="data_access",
            entity_id=f"access_{resource}_{datetime.now().timestamp()}",
            details=access_details,
        )

    def log_integration_event(
        self,
        user_id: str,
        integration_name: str,
        action: AuditAction,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log external integration events"""
        level = AuditLevel.INFO if success else AuditLevel.ERROR

        integration_details = {
            "integration_name": integration_name,
            "success": success,
            **(details or {}),
        }

        self.log_financial_operation(
            user_id=user_id,
            action=action,
            entity_type="integration",
            entity_id=f"integration_{integration_name}_{datetime.now().timestamp()}",
            details=integration_details,
            level=level,
        )

    def get_audit_trail(
        self,
        user_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Retrieve audit trail with filters"""
        try:
            with self.db.get_connection() as conn:
                query = "SELECT * FROM audit_log WHERE 1=1"
                params = []

                if user_id:
                    query += " AND user_id = ?"
                    params.append(user_id)

                if entity_type:
                    query += " AND entity_type = ?"
                    params.append(entity_type)

                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date.isoformat())

                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date.isoformat())

                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)

                cursor = conn.execute(query, params)
                results = []

                for row in cursor.fetchall():
                    audit_entry = dict(row)

                    # Decrypt sensitive details if needed
                    if audit_entry.get("details_encrypted"):
                        try:
                            audit_entry["details"] = (
                                self.secure_storage.retrieve_sensitive_data(
                                    audit_entry["details"], as_dict=True
                                )
                            )
                        except Exception as e:
                            self.logger.error(
                                f"Failed to decrypt audit details: {str(e)}"
                            )
                            audit_entry["details"] = {"error": "Failed to decrypt"}

                    results.append(audit_entry)

                return results

        except Exception as e:
            self.logger.error(f"Failed to retrieve audit trail: {str(e)}")
            return []

    def _store_audit_entry(self, audit_entry: Dict[str, Any]) -> None:
        """Store audit entry in database"""
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_log (
                    timestamp, user_id, action, entity_type, entity_id,
                    amount, currency, level, details, details_encrypted,
                    ip_address, user_agent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    audit_entry["timestamp"],
                    audit_entry["user_id"],
                    audit_entry["action"],
                    audit_entry["entity_type"],
                    audit_entry["entity_id"],
                    audit_entry.get("amount"),
                    audit_entry.get("currency"),
                    audit_entry["level"],
                    (
                        json.dumps(audit_entry["details"])
                        if not audit_entry.get("details_encrypted")
                        else audit_entry["details"]
                    ),
                    audit_entry.get("details_encrypted", False),
                    audit_entry["ip_address"],
                    audit_entry["user_agent"],
                ),
            )

    def _contains_sensitive_data(self, data: Dict[str, Any]) -> bool:
        """Check if data contains sensitive information"""
        sensitive_keys = {
            "password",
            "api_key",
            "secret",
            "token",
            "ssn",
            "credit_card",
            "bank_account",
            "routing_number",
        }

        def check_nested(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if any(sensitive in key.lower() for sensitive in sensitive_keys):
                        return True
                    if check_nested(value, f"{path}.{key}"):
                        return True
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if check_nested(item, f"{path}[{i}]"):
                        return True

            return False

        return check_nested(data)

    def _mask_audit_entry(self, audit_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in audit entry for logging"""
        masked_entry = audit_entry.copy()

        # Mask user_id if it's an email
        if "@" in masked_entry.get("user_id", ""):
            masked_entry["user_id"] = self.secure_storage.mask_pii_in_logs(
                masked_entry["user_id"]
            )

        # Mask details
        if "details" in masked_entry and isinstance(masked_entry["details"], dict):
            masked_details = {}
            for key, value in masked_entry["details"].items():
                if isinstance(value, str):
                    masked_details[key] = self.secure_storage.mask_pii_in_logs(value)
                else:
                    masked_details[key] = value
            masked_entry["details"] = masked_details

        return masked_entry

    def _get_client_ip(self) -> str:
        """Get client IP address"""
        # In production, extract from request headers
        return "127.0.0.1"

    def _get_user_agent(self) -> str:
        """Get user agent string"""
        # In production, extract from request headers
        return "Streamlit/1.28.1"
