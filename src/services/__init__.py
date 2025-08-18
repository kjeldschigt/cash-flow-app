"""
Services package initialization
"""

# Import services with error handling
try:
    from .auth import AuthService
except ImportError:
    AuthService = None

try:
    from .storage import StorageService
except ImportError:
    StorageService = None

try:
    from .stripe import StripeService
except ImportError:
    StripeService = None

try:
    from .airtable import AirtableService
except ImportError:
    AirtableService = None

__all__ = [
    "AuthService",
    "StorageService", 
    "StripeService",
    "AirtableService"
]
