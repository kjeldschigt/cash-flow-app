"""
API Key Test Service - Test connections for various API services
"""

import requests
import json
from typing import Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)

class APIKeyTestService:
    """Service for testing API key connections"""
    
    def __init__(self):
        self.timeout = 10  # 10 second timeout for API calls
        logger.info("API key test service initialized")
    
    def test_stripe_key(self, api_key: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Test Stripe API key by making a simple API call
        
        Args:
            api_key: Stripe API key to test
            
        Returns:
            Tuple of (success, message, details)
        """
        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # Test with a simple balance retrieval
            response = requests.get(
                'https://api.stripe.com/v1/balance',
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                currency = data.get('available', [{}])[0].get('currency', 'unknown')
                logger.info("Stripe API key test successful",
                           operation="test_stripe_key",
                           status_code=response.status_code)
                return True, f"Connection successful (Currency: {currency.upper()})", {
                    'status_code': response.status_code,
                    'currency': currency,
                    'account_type': 'live' if api_key.startswith('sk_live_') else 'test'
                }
            elif response.status_code == 401:
                return False, "Invalid API key - Authentication failed", {
                    'status_code': response.status_code,
                    'error': 'authentication_failed'
                }
            else:
                return False, f"API error (Status: {response.status_code})", {
                    'status_code': response.status_code,
                    'error': 'api_error'
                }
                
        except requests.exceptions.Timeout:
            return False, "Connection timeout - Stripe API unreachable", {'error': 'timeout'}
        except requests.exceptions.ConnectionError:
            return False, "Connection failed - Check internet connection", {'error': 'connection_error'}
        except Exception as e:
            logger.error("Stripe API key test failed",
                        operation="test_stripe_key",
                        error=str(e))
            return False, f"Test failed: {str(e)}", {'error': 'exception'}
    
    def test_openai_key(self, api_key: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Test OpenAI API key by making a simple API call
        
        Args:
            api_key: OpenAI API key to test
            
        Returns:
            Tuple of (success, message, details)
        """
        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Test with models endpoint (lightweight)
            response = requests.get(
                'https://api.openai.com/v1/models',
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                model_count = len(data.get('data', []))
                logger.info("OpenAI API key test successful",
                           operation="test_openai_key",
                           status_code=response.status_code,
                           model_count=model_count)
                return True, f"Connection successful ({model_count} models available)", {
                    'status_code': response.status_code,
                    'model_count': model_count
                }
            elif response.status_code == 401:
                return False, "Invalid API key - Authentication failed", {
                    'status_code': response.status_code,
                    'error': 'authentication_failed'
                }
            else:
                return False, f"API error (Status: {response.status_code})", {
                    'status_code': response.status_code,
                    'error': 'api_error'
                }
                
        except requests.exceptions.Timeout:
            return False, "Connection timeout - OpenAI API unreachable", {'error': 'timeout'}
        except requests.exceptions.ConnectionError:
            return False, "Connection failed - Check internet connection", {'error': 'connection_error'}
        except Exception as e:
            logger.error("OpenAI API key test failed",
                        operation="test_openai_key",
                        error=str(e))
            return False, f"Test failed: {str(e)}", {'error': 'exception'}
    
    def test_airtable_key(self, api_key: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Test Airtable API key by making a simple API call
        
        Args:
            api_key: Airtable API key to test
            
        Returns:
            Tuple of (success, message, details)
        """
        try:
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # Test with bases endpoint (requires API key)
            response = requests.get(
                'https://api.airtable.com/v0/meta/bases',
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                base_count = len(data.get('bases', []))
                logger.info("Airtable API key test successful",
                           operation="test_airtable_key",
                           status_code=response.status_code,
                           base_count=base_count)
                return True, f"Connection successful ({base_count} bases accessible)", {
                    'status_code': response.status_code,
                    'base_count': base_count
                }
            elif response.status_code == 401:
                return False, "Invalid API key - Authentication failed", {
                    'status_code': response.status_code,
                    'error': 'authentication_failed'
                }
            elif response.status_code == 403:
                return False, "API key valid but insufficient permissions", {
                    'status_code': response.status_code,
                    'error': 'insufficient_permissions'
                }
            else:
                return False, f"API error (Status: {response.status_code})", {
                    'status_code': response.status_code,
                    'error': 'api_error'
                }
                
        except requests.exceptions.Timeout:
            return False, "Connection timeout - Airtable API unreachable", {'error': 'timeout'}
        except requests.exceptions.ConnectionError:
            return False, "Connection failed - Check internet connection", {'error': 'connection_error'}
        except Exception as e:
            logger.error("Airtable API key test failed",
                        operation="test_airtable_key",
                        error=str(e))
            return False, f"Test failed: {str(e)}", {'error': 'exception'}
    
    def test_generic_key(self, api_key: str, service_type: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Generic API key test for unsupported services
        
        Args:
            api_key: API key to test
            service_type: Type of service
            
        Returns:
            Tuple of (success, message, details)
        """
        # For generic services, we can only validate format
        if len(api_key) < 10:
            return False, "API key appears to be too short", {'error': 'invalid_format'}
        
        if len(api_key) > 200:
            return False, "API key appears to be too long", {'error': 'invalid_format'}
        
        # Check for suspicious characters
        if any(char in api_key for char in [' ', '\n', '\t', '\r']):
            return False, "API key contains invalid characters", {'error': 'invalid_format'}
        
        logger.info("Generic API key format validation passed",
                   operation="test_generic_key",
                   service_type=service_type)
        
        return True, f"API key format appears valid for {service_type}", {
            'validation_only': True,
            'service_type': service_type
        }
    
    def test_api_key(self, api_key: str, service_type: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Test API key based on service type
        
        Args:
            api_key: API key to test
            service_type: Type of service
            
        Returns:
            Tuple of (success, message, details)
        """
        service_type = service_type.lower()
        
        if service_type == 'stripe':
            return self.test_stripe_key(api_key)
        elif service_type == 'openai':
            return self.test_openai_key(api_key)
        elif service_type == 'airtable':
            return self.test_airtable_key(api_key)
        else:
            return self.test_generic_key(api_key, service_type)

# Global instance
_api_key_test_service = None

def get_api_key_test_service() -> APIKeyTestService:
    """Get global API key test service instance"""
    global _api_key_test_service
    if _api_key_test_service is None:
        _api_key_test_service = APIKeyTestService()
    return _api_key_test_service
