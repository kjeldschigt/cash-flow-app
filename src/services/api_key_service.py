"""
API Key Management Service - Secure CRUD operations for API keys
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import sqlite3
from src.security.api_key_encryption import get_api_key_encryption
import logging
from src.repositories.base import DatabaseConnection

logger = logging.getLogger(__name__)


@dataclass
class APIKeyInfo:
    """API Key information model"""

    id: Optional[int]
    key_name: str
    service_type: str
    added_by_user: str
    created_at: datetime
    last_modified: datetime
    is_active: bool
    description: Optional[str] = None
    masked_value: Optional[str] = None


class APIKeyService:
    """Service for managing API keys with encryption"""

    def __init__(self, db_connection: DatabaseConnection | None = None):
        self.encryption = get_api_key_encryption()
        self.db = db_connection or DatabaseConnection()
        logger.info("API key service initialized", operation="service_init")

    def add_api_key(
        self,
        key_name: str,
        api_key: str,
        service_type: str,
        added_by_user: str,
        description: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Add a new API key with encryption

        Args:
            key_name: Unique name for the API key
            api_key: The actual API key value
            service_type: Type of service (stripe, openai, etc.)
            added_by_user: User ID who added the key
            description: Optional description

        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate API key format
            is_valid, error_msg = self.encryption.validate_api_key_format(
                api_key, service_type
            )
            if not is_valid:
                logger.warning(
                    "Invalid API key format provided",
                    operation="add_api_key",
                    service_type=service_type,
                    error=error_msg,
                )
                return False, error_msg

            # Encrypt the API key
            encrypted_value = self.encryption.encrypt_api_key(api_key)

            # Store in database using DatabaseConnection
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Check if key name already exists
                cursor.execute(
                    "SELECT id FROM api_keys WHERE key_name = ? AND is_active = 1",
                    (key_name,),
                )
                if cursor.fetchone():
                    return False, f"API key with name '{key_name}' already exists"

                # Insert new API key
                cursor.execute(
                    """
                    INSERT INTO api_keys (key_name, encrypted_value, service_type, 
                                        added_by_user, description, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                """,
                    (
                        key_name,
                        encrypted_value,
                        service_type,
                        added_by_user,
                        description,
                    ),
                )

                logger.info(
                    "API key added successfully",
                    operation="add_api_key",
                    key_name=key_name,
                    service_type=service_type,
                    added_by=added_by_user,
                )

                return True, "API key added successfully"

        except Exception as e:
            logger.error(
                "Failed to add API key",
                operation="add_api_key",
                key_name=key_name,
                service_type=service_type,
                error=str(e),
            )
            return False, f"Failed to add API key: {str(e)}"

    def get_api_keys(
        self, service_type: Optional[str] = None, include_inactive: bool = False
    ) -> List[APIKeyInfo]:
        """
        Get list of API keys with masked values

        Args:
            service_type: Filter by service type
            include_inactive: Include inactive keys

        Returns:
            List of APIKeyInfo objects with masked values
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                query = """
                    SELECT id, key_name, encrypted_value, service_type, added_by_user,
                           created_at, last_modified, is_active, description
                    FROM api_keys
                    WHERE 1=1
                """
                params: List[Any] = []

                if not include_inactive:
                    query += " AND is_active = 1"

                if service_type:
                    query += " AND service_type = ?"
                    params.append(service_type)

                query += " ORDER BY created_at DESC"

                cursor.execute(query, params)
                rows = cursor.fetchall()

                api_keys: List[APIKeyInfo] = []
                for row in rows:
                    # Decrypt key to create masked version
                    try:
                        decrypted_key = self.encryption.decrypt_api_key(row["encrypted_value"])  # type: ignore[index]
                        masked_value = self.encryption.mask_api_key(decrypted_key)
                    except Exception as e:
                        logger.error(
                            "Failed to decrypt API key for masking",
                            operation="get_api_keys",
                            key_id=row.get("id"),
                            error=str(e),
                        )
                        masked_value = "****ERROR****"

                    created_val = row.get("created_at")
                    last_mod_val = row.get("last_modified")

                    api_key_info = APIKeyInfo(
                        id=row.get("id"),
                        key_name=row.get("key_name"),
                        service_type=row.get("service_type"),
                        added_by_user=row.get("added_by_user"),
                        created_at=(
                            datetime.fromisoformat(created_val) if created_val else datetime.now()
                        ),
                        last_modified=(
                            datetime.fromisoformat(last_mod_val) if last_mod_val else datetime.now()
                        ),
                        is_active=bool(row.get("is_active")),
                        description=row.get("description"),
                        masked_value=masked_value,
                    )
                    api_keys.append(api_key_info)

                logger.info(
                    "Retrieved API keys",
                    operation="get_api_keys",
                    count=len(api_keys),
                    service_type=service_type,
                )

                return api_keys

        except Exception as e:
            logger.error(
                "Failed to retrieve API keys", operation="get_api_keys", error=str(e)
            )
            return []

    def get_api_key_value(self, key_name: str) -> Optional[str]:
        """
        Get decrypted API key value by name

        Args:
            key_name: Name of the API key

        Returns:
            Decrypted API key value or None if not found
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT encrypted_value FROM api_keys 
                    WHERE key_name = ? AND is_active = 1
                """,
                    (key_name,),
                )

                row = cursor.fetchone()
                if not row:
                    return None

                decrypted_value = self.encryption.decrypt_api_key(row["encrypted_value"])  # type: ignore[index]

                logger.info(
                    "API key value retrieved",
                    operation="get_api_key_value",
                    key_name=key_name,
                )

                return decrypted_value

        except Exception as e:
            logger.error(
                "Failed to retrieve API key value",
                operation="get_api_key_value",
                key_name=key_name,
                error=str(e),
            )
            return None

    def update_api_key(
        self, key_name: str, new_api_key: str, description: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Update an existing API key

        Args:
            key_name: Name of the API key to update
            new_api_key: New API key value
            description: Optional new description

        Returns:
            Tuple of (success, message)
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Check if key exists
                cursor.execute(
                    """
                    SELECT id, service_type FROM api_keys 
                    WHERE key_name = ? AND is_active = 1
                """,
                    (key_name,),
                )

                row = cursor.fetchone()
                if not row:
                    return False, f"API key '{key_name}' not found"

                key_id = row.get("id")
                service_type = row.get("service_type")

                # Validate new API key format
                is_valid, error_msg = self.encryption.validate_api_key_format(
                    new_api_key, service_type
                )
                if not is_valid:
                    return False, error_msg

                # Encrypt new API key
                encrypted_value = self.encryption.encrypt_api_key(new_api_key)

                # Update in database
                if description is not None:
                    cursor.execute(
                        """
                        UPDATE api_keys 
                        SET encrypted_value = ?, description = ?, last_modified = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """,
                        (encrypted_value, description, key_id),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE api_keys 
                        SET encrypted_value = ?, last_modified = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """,
                        (encrypted_value, key_id),
                    )

                logger.info(
                    "API key updated successfully",
                    operation="update_api_key",
                    key_name=key_name,
                    key_id=key_id,
                )

                return True, "API key updated successfully"

        except Exception as e:
            logger.error(
                "Failed to update API key",
                operation="update_api_key",
                key_name=key_name,
                error=str(e),
            )
            return False, f"Failed to update API key: {str(e)}"

    def delete_api_key(self, key_name: str) -> Tuple[bool, str]:
        """
        Soft delete an API key (mark as inactive)

        Args:
            key_name: Name of the API key to delete

        Returns:
            Tuple of (success, message)
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Check if key exists
                cursor.execute(
                    """
                    SELECT id FROM api_keys 
                    WHERE key_name = ? AND is_active = 1
                """,
                    (key_name,),
                )

                row = cursor.fetchone()
                if not row:
                    return False, f"API key '{key_name}' not found"

                key_id = row.get("id")

                # Soft delete (mark as inactive)
                cursor.execute(
                    """
                    UPDATE api_keys 
                    SET is_active = 0, last_modified = CURRENT_TIMESTAMP
                    WHERE id = ?
                """,
                    (key_id,),
                )

                logger.info(
                    "API key deleted successfully",
                    operation="delete_api_key",
                    key_name=key_name,
                    key_id=key_id,
                )

                return True, "API key deleted successfully"

        except Exception as e:
            logger.error(
                "Failed to delete API key",
                operation="delete_api_key",
                key_name=key_name,
                error=str(e),
            )
            return False, f"Failed to delete API key: {str(e)}"

    def get_service_types(self) -> List[str]:
        """Get list of available service types"""
        return [
            "stripe",
            "openai",
            "airtable",
            "twilio",
            "sendgrid",
            "aws",
            "google_cloud",
            "azure",
            "other",
        ]


# Global instance
_api_key_service = None


def get_api_key_service() -> APIKeyService:
    """Get global API key service instance"""
    global _api_key_service
    if _api_key_service is None:
        _api_key_service = APIKeyService()
    return _api_key_service
