"""
Integrated API Service with Smart Fallback System

This service provides a unified interface for all external API integrations
using the smart API key resolver with fallback capabilities.
"""

import logging
from typing import Dict, Optional, Any, Tuple
from contextlib import contextmanager

import streamlit as st

from src.services.api_key_resolver import (
    get_api_key_resolver,
    ResolvedAPIKey,
    APIKeySource,
)

# Configure logging
logger = logging.getLogger(__name__)


class IntegratedAPIService:
    """
    Unified service for managing external API integrations with smart key resolution
    """

    def __init__(self):
        """Initialize the integrated API service"""
        from src.security.auth import AuthManager
        from src.services.user_service import UserService
        # This is a simplified instantiation for service context.
        # In a real app, UserService might need a db connection.
        auth_manager = AuthManager(UserService(None), None) 
        current_user = auth_manager.get_current_user()
        if not current_user:
            raise ValueError("Authentication required for API service")

        self.current_user = current_user
        self.session_id = st.session_state.get("session_id", "default")
        self.resolver = get_api_key_resolver(self.session_id, current_user.id)

    @contextmanager
    def get_stripe_client(self):
        """
        Get configured Stripe client with smart key resolution

        Yields:
            Tuple of (stripe_client, resolved_key_info) or (None, error_info)
        """
        try:
            import stripe
        except ImportError:
            yield None, {
                "error": "Stripe library not installed. Run: pip install stripe"
            }
            return

        with self.resolver.get_api_key("stripe_api_key", "stripe") as resolved_key:
            if not resolved_key.is_valid:
                yield None, {
                    "error": f"Stripe API key not found: {resolved_key.error_message}",
                    "source": resolved_key.source.value,
                }
                return

            # Configure Stripe
            stripe.api_key = resolved_key.key_value

            try:
                # Test the connection
                stripe.Account.retrieve()

                yield stripe, {
                    "success": True,
                    "source": resolved_key.source.value,
                    "masked_key": resolved_key.masked_value,
                }
            except stripe.error.AuthenticationError as e:
                yield None, {
                    "error": f"Stripe authentication failed: {str(e)}",
                    "source": resolved_key.source.value,
                }
            except Exception as e:
                yield None, {
                    "error": f"Stripe connection error: {str(e)}",
                    "source": resolved_key.source.value,
                }

    @contextmanager
    def get_openai_client(self):
        """
        Get configured OpenAI client with smart key resolution

        Yields:
            Tuple of (openai_client, resolved_key_info) or (None, error_info)
        """
        try:
            import openai
        except ImportError:
            yield None, {
                "error": "OpenAI library not installed. Run: pip install openai"
            }
            return

        with self.resolver.get_api_key("openai_api_key", "openai") as resolved_key:
            if not resolved_key.is_valid:
                yield None, {
                    "error": f"OpenAI API key not found: {resolved_key.error_message}",
                    "source": resolved_key.source.value,
                }
                return

            # Configure OpenAI client
            client = openai.OpenAI(api_key=resolved_key.key_value)

            try:
                # Test the connection
                client.models.list()

                yield client, {
                    "success": True,
                    "source": resolved_key.source.value,
                    "masked_key": resolved_key.masked_value,
                }
            except openai.AuthenticationError as e:
                yield None, {
                    "error": f"OpenAI authentication failed: {str(e)}",
                    "source": resolved_key.source.value,
                }
            except Exception as e:
                yield None, {
                    "error": f"OpenAI connection error: {str(e)}",
                    "source": resolved_key.source.value,
                }

    @contextmanager
    def get_airtable_client(self):
        """
        Get configured Airtable client with smart key resolution

        Yields:
            Tuple of (airtable_session, resolved_key_info) or (None, error_info)
        """
        try:
            import requests
        except ImportError:
            yield None, {
                "error": "Requests library not installed. Run: pip install requests"
            }
            return

        with self.resolver.get_api_key("airtable_api_key", "airtable") as resolved_key:
            if not resolved_key.is_valid:
                yield None, {
                    "error": f"Airtable API key not found: {resolved_key.error_message}",
                    "source": resolved_key.source.value,
                }
                return

            # Create Airtable session
            session = requests.Session()
            session.headers.update(
                {
                    "Authorization": f"Bearer {resolved_key.key_value}",
                    "Content-Type": "application/json",
                }
            )

            try:
                # Test the connection
                response = session.get("https://api.airtable.com/v0/meta/bases")
                if response.status_code == 200:
                    yield session, {
                        "success": True,
                        "source": resolved_key.source.value,
                        "masked_key": resolved_key.masked_value,
                    }
                else:
                    yield None, {
                        "error": f"Airtable authentication failed: {response.status_code}",
                        "source": resolved_key.source.value,
                    }
            except Exception as e:
                yield None, {
                    "error": f"Airtable connection error: {str(e)}",
                    "source": resolved_key.source.value,
                }

    @contextmanager
    def get_sendgrid_client(self):
        """
        Get configured SendGrid client with smart key resolution

        Yields:
            Tuple of (sendgrid_client, resolved_key_info) or (None, error_info)
        """
        try:
            import sendgrid
            from sendgrid.helpers.mail import Mail
        except ImportError:
            yield None, {
                "error": "SendGrid library not installed. Run: pip install sendgrid"
            }
            return

        with self.resolver.get_api_key("sendgrid_api_key", "sendgrid") as resolved_key:
            if not resolved_key.is_valid:
                yield None, {
                    "error": f"SendGrid API key not found: {resolved_key.error_message}",
                    "source": resolved_key.source.value,
                }
                return

            # Configure SendGrid
            sg = sendgrid.SendGridAPIClient(api_key=resolved_key.key_value)

            try:
                # Test the connection
                response = sg.client.user.profile.get()
                if response.status_code == 200:
                    yield sg, {
                        "success": True,
                        "source": resolved_key.source.value,
                        "masked_key": resolved_key.masked_value,
                    }
                else:
                    yield None, {
                        "error": f"SendGrid authentication failed: {response.status_code}",
                        "source": resolved_key.source.value,
                    }
            except Exception as e:
                yield None, {
                    "error": f"SendGrid connection error: {str(e)}",
                    "source": resolved_key.source.value,
                }

    def get_service_status(self, service_type: str) -> Dict[str, Any]:
        """
        Get the current status of a service integration

        Args:
            service_type: Type of service (stripe, openai, etc.)

        Returns:
            Dictionary with service status information
        """
        resolved_key = self.resolver.resolve_api_key(
            f"{service_type}_api_key", service_type
        )

        status = {
            "service_type": service_type,
            "is_configured": resolved_key.is_valid,
            "source": resolved_key.source.value,
            "masked_key": resolved_key.masked_value if resolved_key.is_valid else None,
            "error": resolved_key.error_message if not resolved_key.is_valid else None,
        }

        return status

    def get_all_service_statuses(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status for all supported services

        Returns:
            Dictionary mapping service types to their status information
        """
        services = [
            "stripe",
            "openai",
            "airtable",
            "twilio",
            "sendgrid",
            "aws",
            "google_cloud",
            "azure",
        ]
        statuses = {}

        for service in services:
            statuses[service] = self.get_service_status(service)

        return statuses

    def validate_service_configuration(
        self, service_type: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validate a service configuration by testing the API key

        Args:
            service_type: Type of service to validate

        Returns:
            Tuple of (is_valid, message, details)
        """
        try:
            if service_type == "stripe":
                with self.get_stripe_client() as (client, info):
                    if client:
                        return True, "Stripe connection successful", info
                    else:
                        return False, info.get("error", "Unknown error"), info

            elif service_type == "openai":
                with self.get_openai_client() as (client, info):
                    if client:
                        return True, "OpenAI connection successful", info
                    else:
                        return False, info.get("error", "Unknown error"), info

            elif service_type == "airtable":
                with self.get_airtable_client() as (session, info):
                    if session:
                        return True, "Airtable connection successful", info
                    else:
                        return False, info.get("error", "Unknown error"), info

            elif service_type == "sendgrid":
                with self.get_sendgrid_client() as (client, info):
                    if client:
                        return True, "SendGrid connection successful", info
                    else:
                        return False, info.get("error", "Unknown error"), info

            else:
                # For other services, just check if key exists
                resolved_key = self.resolver.resolve_api_key(
                    f"{service_type}_api_key", service_type
                )
                if resolved_key.is_valid:
                    return (
                        True,
                        f"{service_type.title()} API key found",
                        {
                            "source": resolved_key.source.value,
                            "masked_key": resolved_key.masked_value,
                        },
                    )
                else:
                    return (
                        False,
                        resolved_key.error_message or "API key not found",
                        {"source": resolved_key.source.value},
                    )

        except Exception as e:
            logger.error(f"Error validating {service_type} configuration: {e}")
            return False, f"Validation error: {str(e)}", {"error": str(e)}

    def refresh_service_cache(self, service_type: str = None):
        """
        Refresh the cache for a specific service or all services

        Args:
            service_type: Specific service to refresh, or None for all services
        """
        if service_type:
            self.resolver.invalidate_cache(service_type=service_type)
        else:
            self.resolver.invalidate_cache()

    def get_configuration_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all service configurations and their sources

        Returns:
            Dictionary with configuration summary
        """
        statuses = self.get_all_service_statuses()

        summary = {
            "total_services": len(statuses),
            "configured_services": len(
                [s for s in statuses.values() if s["is_configured"]]
            ),
            "source_breakdown": {},
            "services": statuses,
        }

        # Count services by source
        for status in statuses.values():
            if status["is_configured"]:
                source = status["source"]
                summary["source_breakdown"][source] = (
                    summary["source_breakdown"].get(source, 0) + 1
                )

        return summary


# Global service instance
_api_service_instance = None


def get_integrated_api_service() -> IntegratedAPIService:
    """
    Get or create the integrated API service instance

    Returns:
        IntegratedAPIService instance
    """
    global _api_service_instance

    try:
        if _api_service_instance is None:
            _api_service_instance = IntegratedAPIService()
        return _api_service_instance
    except Exception as e:
        logger.error(f"Failed to initialize integrated API service: {e}")
        raise


def clear_api_service_cache():
    """Clear the API service cache"""
    global _api_service_instance
    _api_service_instance = None
