"""
Smart API Key Resolver with Fallback System

This service provides a hierarchical API key resolution system that checks:
1. UI Database (KeyVaultService) - highest priority
2. Environment Variables - fallback
3. Streamlit Secrets - platform fallback

Features:
- Session-based caching for performance
- Source tracking for transparency
- Validation and error handling
- Support for all integrated services
"""

import os
import logging
from typing import Dict, Optional, Tuple, Any, NamedTuple
from enum import Enum
from dataclasses import dataclass
from contextlib import contextmanager
import streamlit as st

from src.services.key_vault import get_key_vault_service
from src.security.api_key_encryption import get_api_key_encryption

# Configure logging
logger = logging.getLogger(__name__)


class APIKeySource(Enum):
    """Enumeration of API key sources in order of preference"""

    DATABASE = "database"
    ENVIRONMENT = "environment"
    STREAMLIT_SECRETS = "streamlit_secrets"
    NOT_FOUND = "not_found"


@dataclass
class ResolvedAPIKey:
    """Container for resolved API key information"""

    key_value: Optional[str]
    source: APIKeySource
    service_type: str
    key_name: str
    masked_value: Optional[str] = None
    is_valid: bool = False
    error_message: Optional[str] = None

    def __post_init__(self):
        """Post-initialization to set masked value and validation"""
        if self.key_value:
            try:
                encryption_service = get_api_key_encryption()
                self.masked_value = encryption_service.mask_api_key(self.key_value)
                self.is_valid = True
            except Exception:
                self.masked_value = (
                    f"****{self.key_value[-4:] if len(self.key_value) > 4 else '****'}"
                )
                self.is_valid = True
        else:
            self.masked_value = None
            self.is_valid = False


class APIKeyResolver:
    """
    Smart API Key Resolver with hierarchical fallback system
    """

    # Environment variable mappings for each service
    ENV_VAR_MAPPINGS = {
        "stripe": ["STRIPE_SECRET_KEY", "STRIPE_API_KEY", "STRIPE_SK"],
        "openai": ["OPENAI_API_KEY", "OPENAI_SECRET_KEY"],
        "airtable": ["AIRTABLE_API_KEY", "AIRTABLE_TOKEN"],
        "twilio": ["TWILIO_AUTH_TOKEN", "TWILIO_API_KEY"],
        "sendgrid": ["SENDGRID_API_KEY", "SENDGRID_TOKEN"],
        "aws": ["AWS_SECRET_ACCESS_KEY", "AWS_ACCESS_KEY_ID"],
        "google_cloud": ["GOOGLE_CLOUD_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS"],
        "azure": ["AZURE_CLIENT_SECRET", "AZURE_API_KEY"],
    }

    # Streamlit secrets mappings
    SECRETS_MAPPINGS = {
        "stripe": ["stripe_secret_key", "stripe_api_key"],
        "openai": ["openai_api_key", "openai_secret_key"],
        "airtable": ["airtable_api_key", "airtable_token"],
        "twilio": ["twilio_auth_token", "twilio_api_key"],
        "sendgrid": ["sendgrid_api_key", "sendgrid_token"],
        "aws": ["aws_secret_access_key", "aws_access_key_id"],
        "google_cloud": ["google_cloud_api_key", "google_application_credentials"],
        "azure": ["azure_client_secret", "azure_api_key"],
    }

    def __init__(self, session_id: str, user_id: int):
        """
        Initialize the API Key Resolver

        Args:
            session_id: Current session identifier
            user_id: Current user identifier
        """
        self.session_id = session_id
        self.user_id = user_id
        self._cache_key = f"api_key_resolver_cache_{session_id}"

        # Initialize vault service for database lookups
        try:
            self.vault_service = get_key_vault_service(session_id, user_id)
        except Exception as e:
            logger.warning(f"Failed to initialize vault service: {e}")
            self.vault_service = None

    def _get_cache(self) -> Dict[str, ResolvedAPIKey]:
        """Get the session cache for resolved API keys"""
        if self._cache_key not in st.session_state:
            st.session_state[self._cache_key] = {}
        return st.session_state[self._cache_key]

    def _set_cache(self, key_name: str, resolved_key: ResolvedAPIKey):
        """Cache a resolved API key for the session"""
        cache = self._get_cache()
        cache[key_name] = resolved_key

    def _clear_cache(self):
        """Clear the resolver cache"""
        if self._cache_key in st.session_state:
            del st.session_state[self._cache_key]

    def _check_database_source(self, key_name: str, service_type: str) -> Optional[str]:
        """
        Check for API key in the database via KeyVaultService

        Args:
            key_name: Name of the API key
            service_type: Type of service (stripe, openai, etc.)

        Returns:
            API key value if found, None otherwise
        """
        if not self.vault_service:
            return None

        try:
            with self.vault_service.retrieve_api_key(key_name) as key_context:
                if key_context and key_context.service_type == service_type:
                    return key_context.key_value
        except Exception as e:
            logger.debug(f"Database lookup failed for {key_name}: {e}")

        return None

    def _check_environment_source(self, service_type: str) -> Optional[str]:
        """
        Check for API key in environment variables

        Args:
            service_type: Type of service (stripe, openai, etc.)

        Returns:
            API key value if found, None otherwise
        """
        env_vars = self.ENV_VAR_MAPPINGS.get(service_type, [])

        for env_var in env_vars:
            value = os.getenv(env_var)
            if value and value.strip():
                logger.debug(
                    f"Found {service_type} key in environment variable {env_var}"
                )
                return value.strip()

        return None

    def _check_streamlit_secrets(self, service_type: str) -> Optional[str]:
        """
        Check for API key in Streamlit secrets

        Args:
            service_type: Type of service (stripe, openai, etc.)

        Returns:
            API key value if found, None otherwise
        """
        if not hasattr(st, "secrets"):
            return None

        secret_keys = self.SECRETS_MAPPINGS.get(service_type, [])

        for secret_key in secret_keys:
            try:
                value = st.secrets.get(secret_key)
                if value and str(value).strip():
                    logger.debug(
                        f"Found {service_type} key in Streamlit secrets {secret_key}"
                    )
                    return str(value).strip()
            except Exception as e:
                logger.debug(f"Failed to access Streamlit secret {secret_key}: {e}")

        return None

    def resolve_api_key(
        self, key_name: str, service_type: str, use_cache: bool = True
    ) -> ResolvedAPIKey:
        """
        Resolve an API key using the hierarchical fallback system

        Args:
            key_name: Name of the API key
            service_type: Type of service (stripe, openai, etc.)
            use_cache: Whether to use cached results

        Returns:
            ResolvedAPIKey object with key value and source information
        """
        # Check cache first if enabled
        if use_cache:
            cache = self._get_cache()
            cache_key = f"{key_name}_{service_type}"
            if cache_key in cache:
                logger.debug(f"Using cached result for {key_name}")
                return cache[cache_key]

        # 1. Check database (highest priority)
        api_key = self._check_database_source(key_name, service_type)
        if api_key:
            resolved = ResolvedAPIKey(
                key_value=api_key,
                source=APIKeySource.DATABASE,
                service_type=service_type,
                key_name=key_name,
            )
            if use_cache:
                self._set_cache(f"{key_name}_{service_type}", resolved)
            return resolved

        # 2. Check environment variables (fallback)
        api_key = self._check_environment_source(service_type)
        if api_key:
            resolved = ResolvedAPIKey(
                key_value=api_key,
                source=APIKeySource.ENVIRONMENT,
                service_type=service_type,
                key_name=key_name,
            )
            if use_cache:
                self._set_cache(f"{key_name}_{service_type}", resolved)
            return resolved

        # 3. Check Streamlit secrets (platform fallback)
        api_key = self._check_streamlit_secrets(service_type)
        if api_key:
            resolved = ResolvedAPIKey(
                key_value=api_key,
                source=APIKeySource.STREAMLIT_SECRETS,
                service_type=service_type,
                key_name=key_name,
            )
            if use_cache:
                self._set_cache(f"{key_name}_{service_type}", resolved)
            return resolved

        # 4. Not found in any source
        resolved = ResolvedAPIKey(
            key_value=None,
            source=APIKeySource.NOT_FOUND,
            service_type=service_type,
            key_name=key_name,
            error_message=f"API key not found in any source for {service_type}",
        )
        if use_cache:
            self._set_cache(f"{key_name}_{service_type}", resolved)
        return resolved

    @contextmanager
    def get_api_key(self, key_name: str, service_type: str, use_cache: bool = True):
        """
        Context manager for secure API key retrieval

        Args:
            key_name: Name of the API key
            service_type: Type of service (stripe, openai, etc.)
            use_cache: Whether to use cached results

        Yields:
            ResolvedAPIKey object
        """
        resolved_key = self.resolve_api_key(key_name, service_type, use_cache)
        try:
            yield resolved_key
        finally:
            # Secure cleanup - overwrite key value in memory
            if resolved_key.key_value:
                resolved_key.key_value = "0" * len(resolved_key.key_value)
                resolved_key.key_value = None

    def get_all_resolved_keys(
        self, service_types: list = None
    ) -> Dict[str, ResolvedAPIKey]:
        """
        Get all resolved API keys for specified services

        Args:
            service_types: List of service types to check. If None, checks all supported services.

        Returns:
            Dictionary mapping service types to resolved API keys
        """
        if service_types is None:
            service_types = list(self.ENV_VAR_MAPPINGS.keys())

        resolved_keys = {}

        for service_type in service_types:
            # Use service type as default key name
            key_name = f"{service_type}_api_key"
            resolved_key = self.resolve_api_key(key_name, service_type)
            resolved_keys[service_type] = resolved_key

        return resolved_keys

    def get_source_priority_info(self) -> Dict[str, Any]:
        """
        Get information about the source priority system

        Returns:
            Dictionary with priority information and available sources
        """
        return {
            "priority_order": [
                {
                    "source": "Database (UI)",
                    "priority": 1,
                    "description": "Keys stored via Settings UI",
                },
                {
                    "source": "Environment Variables",
                    "priority": 2,
                    "description": "System environment variables",
                },
                {
                    "source": "Streamlit Secrets",
                    "priority": 3,
                    "description": "Streamlit Cloud secrets",
                },
            ],
            "supported_services": list(self.ENV_VAR_MAPPINGS.keys()),
            "environment_mappings": self.ENV_VAR_MAPPINGS,
            "secrets_mappings": self.SECRETS_MAPPINGS,
        }

    def invalidate_cache(self, key_name: str = None, service_type: str = None):
        """
        Invalidate cache entries

        Args:
            key_name: Specific key name to invalidate. If None, invalidates all.
            service_type: Specific service type to invalidate. If None, invalidates all.
        """
        if key_name is None and service_type is None:
            self._clear_cache()
            return

        cache = self._get_cache()
        if key_name and service_type:
            cache_key = f"{key_name}_{service_type}"
            if cache_key in cache:
                del cache[cache_key]
        else:
            # Partial invalidation
            keys_to_remove = []
            for cache_key in cache.keys():
                if (key_name and key_name in cache_key) or (
                    service_type and service_type in cache_key
                ):
                    keys_to_remove.append(cache_key)

            for key in keys_to_remove:
                del cache[key]


# Global resolver instance management
_resolver_instances = {}


def get_api_key_resolver(session_id: str, user_id: int) -> APIKeyResolver:
    """
    Get or create an API key resolver instance for the session

    Args:
        session_id: Current session identifier
        user_id: Current user identifier

    Returns:
        APIKeyResolver instance
    """
    resolver_key = f"{session_id}_{user_id}"

    if resolver_key not in _resolver_instances:
        _resolver_instances[resolver_key] = APIKeyResolver(session_id, user_id)

    return _resolver_instances[resolver_key]


def clear_resolver_cache(session_id: str, user_id: int = None):
    """
    Clear resolver cache for a session

    Args:
        session_id: Session identifier
        user_id: User identifier (optional)
    """
    if user_id:
        resolver_key = f"{session_id}_{user_id}"
        if resolver_key in _resolver_instances:
            _resolver_instances[resolver_key].invalidate_cache()
    else:
        # Clear all resolvers for the session
        keys_to_remove = [
            k for k in _resolver_instances.keys() if k.startswith(f"{session_id}_")
        ]
        for key in keys_to_remove:
            _resolver_instances[key].invalidate_cache()
