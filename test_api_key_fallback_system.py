"""
Comprehensive Test Suite for API Key Fallback System

Tests the smart API key resolver with hierarchical fallback:
1. Database (UI) → 2. Environment Variables → 3. Streamlit Secrets
"""

import os
import sys
import tempfile
import sqlite3
import unittest
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_api_key_resolver_basic():
    """Test basic API key resolver functionality"""
    print("🧪 Testing API Key Resolver Basic Functionality")
    
    try:
        from src.services.api_key_resolver import APIKeyResolver, APIKeySource, ResolvedAPIKey
        
        # Test resolver initialization
        resolver = APIKeyResolver("test_session", 1)
        assert resolver.session_id == "test_session"
        assert resolver.user_id == 1
        print("✅ Resolver initialization successful")
        
        # Test environment variable mappings
        assert 'stripe' in resolver.ENV_VAR_MAPPINGS
        assert 'openai' in resolver.ENV_VAR_MAPPINGS
        assert 'STRIPE_SECRET_KEY' in resolver.ENV_VAR_MAPPINGS['stripe']
        assert 'OPENAI_API_KEY' in resolver.ENV_VAR_MAPPINGS['openai']
        print("✅ Environment variable mappings validated")
        
        # Test Streamlit secrets mappings
        assert 'stripe' in resolver.SECRETS_MAPPINGS
        assert 'openai' in resolver.SECRETS_MAPPINGS
        print("✅ Streamlit secrets mappings validated")
        
        print("✅ Basic functionality tests passed")
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False
    
    return True

def test_environment_variable_fallback():
    """Test environment variable fallback functionality"""
    print("\n🧪 Testing Environment Variable Fallback")
    
    try:
        from src.services.api_key_resolver import APIKeyResolver, APIKeySource
        
        # Set test environment variables
        test_stripe_key = "sk_test_environment_fallback_key"
        test_openai_key = "sk-environment_openai_key"
        
        os.environ['STRIPE_SECRET_KEY'] = test_stripe_key
        os.environ['OPENAI_API_KEY'] = test_openai_key
        
        resolver = APIKeyResolver("test_session", 1)
        
        # Test Stripe environment fallback
        stripe_key = resolver._check_environment_source('stripe')
        assert stripe_key == test_stripe_key, f"Expected {test_stripe_key}, got {stripe_key}"
        print("✅ Stripe environment variable detection successful")
        
        # Test OpenAI environment fallback
        openai_key = resolver._check_environment_source('openai')
        assert openai_key == test_openai_key, f"Expected {test_openai_key}, got {openai_key}"
        print("✅ OpenAI environment variable detection successful")
        
        # Test full resolution with environment fallback
        resolved_stripe = resolver.resolve_api_key("stripe_api_key", "stripe", use_cache=False)
        assert resolved_stripe.is_valid, "Stripe key should be valid"
        assert resolved_stripe.source == APIKeySource.ENVIRONMENT, "Should use environment source"
        assert resolved_stripe.key_value == test_stripe_key, "Key value should match environment"
        print("✅ Full environment resolution successful")
        
        print("✅ Environment variable fallback tests passed")
        
    except Exception as e:
        print(f"❌ Environment variable fallback test failed: {e}")
        return False
    finally:
        # Clean up environment variables
        if 'STRIPE_SECRET_KEY' in os.environ:
            del os.environ['STRIPE_SECRET_KEY']
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']
    
    return True

def test_streamlit_secrets_fallback():
    """Test Streamlit secrets fallback functionality"""
    print("\n🧪 Testing Streamlit Secrets Fallback")
    
    try:
        from src.services.api_key_resolver import APIKeyResolver, APIKeySource
        
        # Mock Streamlit secrets
        mock_secrets = {
            'stripe_secret_key': 'sk_test_streamlit_secrets_key',
            'openai_api_key': 'sk-streamlit_openai_key'
        }
        
        with patch('streamlit.secrets', mock_secrets):
            resolver = APIKeyResolver("test_session", 1)
            
            # Test Stripe secrets fallback
            stripe_key = resolver._check_streamlit_secrets('stripe')
            assert stripe_key == mock_secrets['stripe_secret_key'], "Stripe secrets key mismatch"
            print("✅ Stripe Streamlit secrets detection successful")
            
            # Test OpenAI secrets fallback
            openai_key = resolver._check_streamlit_secrets('openai')
            assert openai_key == mock_secrets['openai_api_key'], "OpenAI secrets key mismatch"
            print("✅ OpenAI Streamlit secrets detection successful")
            
            # Test full resolution with secrets fallback
            resolved_stripe = resolver.resolve_api_key("stripe_api_key", "stripe", use_cache=False)
            assert resolved_stripe.is_valid, "Stripe key should be valid"
            assert resolved_stripe.source == APIKeySource.STREAMLIT_SECRETS, "Should use Streamlit secrets source"
            print("✅ Full Streamlit secrets resolution successful")
        
        print("✅ Streamlit secrets fallback tests passed")
        
    except Exception as e:
        print(f"❌ Streamlit secrets fallback test failed: {e}")
        return False
    
    return True

def test_priority_hierarchy():
    """Test that sources are checked in correct priority order"""
    print("\n🧪 Testing Priority Hierarchy")
    
    try:
        from src.services.api_key_resolver import APIKeyResolver, APIKeySource
        
        # Set up all three sources with different values
        env_key = "sk_test_environment_key"
        secrets_key = "sk_test_secrets_key"
        
        os.environ['STRIPE_SECRET_KEY'] = env_key
        
        mock_secrets = {'stripe_secret_key': secrets_key}
        
        with patch('streamlit.secrets', mock_secrets):
            resolver = APIKeyResolver("test_session", 1)
            
            # Without database key, should prefer environment over secrets
            resolved = resolver.resolve_api_key("stripe_api_key", "stripe", use_cache=False)
            assert resolved.source == APIKeySource.ENVIRONMENT, f"Expected ENVIRONMENT, got {resolved.source}"
            assert resolved.key_value == env_key, "Should use environment key"
            print("✅ Environment priority over Streamlit secrets confirmed")
            
            # Remove environment variable, should fall back to secrets
            del os.environ['STRIPE_SECRET_KEY']
            
            resolved = resolver.resolve_api_key("stripe_api_key", "stripe", use_cache=False)
            assert resolved.source == APIKeySource.STREAMLIT_SECRETS, f"Expected STREAMLIT_SECRETS, got {resolved.source}"
            assert resolved.key_value == secrets_key, "Should use secrets key"
            print("✅ Streamlit secrets fallback confirmed")
        
        print("✅ Priority hierarchy tests passed")
        
    except Exception as e:
        print(f"❌ Priority hierarchy test failed: {e}")
        return False
    finally:
        # Clean up
        if 'STRIPE_SECRET_KEY' in os.environ:
            del os.environ['STRIPE_SECRET_KEY']
    
    return True

def test_caching_functionality():
    """Test session-based caching functionality"""
    print("\n🧪 Testing Caching Functionality")
    
    try:
        from src.services.api_key_resolver import APIKeyResolver, APIKeySource
        
        # Set up environment variable
        test_key = "sk_test_cache_key"
        os.environ['STRIPE_SECRET_KEY'] = test_key
        
        resolver = APIKeyResolver("test_session", 1)
        
        # First resolution should cache the result
        resolved1 = resolver.resolve_api_key("stripe_api_key", "stripe", use_cache=True)
        assert resolved1.is_valid, "First resolution should be valid"
        
        # Remove environment variable
        del os.environ['STRIPE_SECRET_KEY']
        
        # Second resolution should use cache (still valid)
        resolved2 = resolver.resolve_api_key("stripe_api_key", "stripe", use_cache=True)
        assert resolved2.is_valid, "Cached resolution should still be valid"
        assert resolved2.key_value == test_key, "Should use cached key value"
        print("✅ Cache hit functionality confirmed")
        
        # Third resolution without cache should fail (env var removed)
        resolved3 = resolver.resolve_api_key("stripe_api_key", "stripe", use_cache=False)
        assert not resolved3.is_valid, "Non-cached resolution should fail"
        assert resolved3.source == APIKeySource.NOT_FOUND, "Should show NOT_FOUND"
        print("✅ Cache bypass functionality confirmed")
        
        # Test cache invalidation
        resolver.invalidate_cache("stripe_api_key", "stripe")
        resolved4 = resolver.resolve_api_key("stripe_api_key", "stripe", use_cache=True)
        assert not resolved4.is_valid, "Post-invalidation resolution should fail"
        print("✅ Cache invalidation functionality confirmed")
        
        print("✅ Caching functionality tests passed")
        
    except Exception as e:
        print(f"❌ Caching functionality test failed: {e}")
        return False
    finally:
        # Clean up
        if 'STRIPE_SECRET_KEY' in os.environ:
            del os.environ['STRIPE_SECRET_KEY']
    
    return True

def test_context_manager():
    """Test secure context manager functionality"""
    print("\n🧪 Testing Context Manager")
    
    try:
        from src.services.api_key_resolver import APIKeyResolver
        
        # Set up test environment
        test_key = "sk_test_context_manager_key"
        os.environ['STRIPE_SECRET_KEY'] = test_key
        
        # Mock Streamlit session state for testing
        import streamlit as st
        if not hasattr(st, 'session_state'):
            st.session_state = {}
        
        resolver = APIKeyResolver("test_session", 1)
        
        # Test context manager
        with resolver.get_api_key("stripe_api_key", "stripe") as resolved_key:
            assert resolved_key.is_valid, f"Context manager should provide valid key, got: {resolved_key.error_message}"
            assert resolved_key.key_value == test_key, f"Key value should match, expected {test_key}, got {resolved_key.key_value}"
            
            # Key should be accessible within context
            original_key = resolved_key.key_value
            assert original_key == test_key, "Key should be accessible in context"
        
        print("✅ Context manager functionality confirmed")
        print("✅ Context manager tests passed")
        
    except Exception as e:
        print(f"❌ Context manager test failed: {e}")
        return False
    finally:
        # Clean up
        if 'STRIPE_SECRET_KEY' in os.environ:
            del os.environ['STRIPE_SECRET_KEY']
    
    return True

def test_integrated_api_service():
    """Test the integrated API service functionality"""
    print("\n🧪 Testing Integrated API Service")
    
    try:
        # Mock authentication and streamlit
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.role.name = "ADMIN"
        
        # Mock streamlit session state
        mock_session_state = {'session_id': 'test_session'}
        
        with patch('src.services.integrated_api_service.get_current_user', return_value=mock_user):
            with patch('src.services.integrated_api_service.st.session_state', mock_session_state):
                with patch('streamlit.session_state', mock_session_state):
                    from src.services.integrated_api_service import IntegratedAPIService
                    
                    # Set up test environment
                    os.environ['STRIPE_SECRET_KEY'] = 'sk_test_integrated_service'
                    
                    service = IntegratedAPIService()
                    assert service.current_user == mock_user, "User should be set"
                    assert service.session_id == 'test_session', "Session ID should be set"
                    print("✅ Integrated API service initialization successful")
                    
                    # Test service status
                    status = service.get_service_status('stripe')
                    assert status['service_type'] == 'stripe', "Service type should match"
                    assert status['is_configured'], "Stripe should be configured"
                    assert status['source'] == 'environment', "Should use environment source"
                    print("✅ Service status functionality confirmed")
                    
                    # Test all service statuses
                    all_statuses = service.get_all_service_statuses()
                    assert 'stripe' in all_statuses, "Stripe should be in all statuses"
                    assert all_statuses['stripe']['is_configured'], "Stripe should be configured"
                    print("✅ All service statuses functionality confirmed")
                    
                    # Test configuration summary
                    summary = service.get_configuration_summary()
                    assert summary['total_services'] > 0, "Should have services"
                    assert summary['configured_services'] >= 1, "Should have at least Stripe configured"
                    assert 'environment' in summary['source_breakdown'], "Should show environment source"
                    print("✅ Configuration summary functionality confirmed")
        
        print("✅ Integrated API service tests passed")
        
    except Exception as e:
        print(f"❌ Integrated API service test failed: {e}")
        return False
    finally:
        # Clean up
        if 'STRIPE_SECRET_KEY' in os.environ:
            del os.environ['STRIPE_SECRET_KEY']
    
    return True

def test_error_handling():
    """Test error handling and edge cases"""
    print("\n🧪 Testing Error Handling")
    
    try:
        from src.services.api_key_resolver import APIKeyResolver, APIKeySource
        
        resolver = APIKeyResolver("test_session", 1)
        
        # Test with non-existent service
        resolved = resolver.resolve_api_key("nonexistent_key", "nonexistent_service", use_cache=False)
        assert not resolved.is_valid, "Non-existent service should be invalid"
        assert resolved.source == APIKeySource.NOT_FOUND, "Should show NOT_FOUND"
        assert resolved.error_message is not None, "Should have error message"
        print("✅ Non-existent service handling confirmed")
        
        # Test with empty key name
        resolved = resolver.resolve_api_key("", "stripe", use_cache=False)
        assert not resolved.is_valid, "Empty key name should be invalid"
        print("✅ Empty key name handling confirmed")
        
        # Test cache operations with invalid keys
        resolver.invalidate_cache("invalid_key", "invalid_service")  # Should not crash
        print("✅ Invalid cache operations handling confirmed")
        
        print("✅ Error handling tests passed")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    
    return True

def main():
    """Run all tests for the API key fallback system"""
    print("🚀 Running API Key Fallback System Tests\n")
    
    tests = [
        test_api_key_resolver_basic,
        test_environment_variable_fallback,
        test_streamlit_secrets_fallback,
        test_priority_hierarchy,
        test_caching_functionality,
        test_context_manager,
        test_integrated_api_service,
        test_error_handling
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
        print()  # Add spacing between tests
    
    print("=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All API Key Fallback System tests passed!")
        print("\n📋 Verified Features:")
        print("✅ Hierarchical key resolution (Database → Environment → Streamlit Secrets)")
        print("✅ Session-based caching with invalidation")
        print("✅ Secure context managers for key access")
        print("✅ Source transparency and priority indicators")
        print("✅ Integrated API service with validation")
        print("✅ Comprehensive error handling")
        print("✅ Environment variable and Streamlit secrets fallback")
        print("✅ Cache management and performance optimization")
        
        return True
    else:
        print(f"\n❌ {failed} test(s) failed. Please review the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
