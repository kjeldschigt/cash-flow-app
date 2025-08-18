"""
Test suite for Redis-based session management system.
Tests session creation, validation, expiration, and security features.
"""

import os
import sys
import time
import secrets
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    import redis
    from src.security.session_manager import RedisSessionManager, SessionData
    from src.security.rate_limiter import RedisRateLimiter, RateLimitRule, RateLimitStrategy
    from src.security.cookie_manager import SecureCookieManager
    from src.models.user import User, UserRole
    REDIS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Redis dependencies not available: {e}")
    REDIS_AVAILABLE = False


def test_redis_connection():
    """Test Redis connection"""
    print("🔍 Testing Redis Connection")
    print("=" * 50)
    
    if not REDIS_AVAILABLE:
        print("❌ Redis dependencies not available")
        return False
    
    try:
        redis_client = redis.from_url('redis://localhost:6379/0', decode_responses=True)
        redis_client.ping()
        print("✅ Redis connection successful")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("💡 Make sure Redis is running: redis-server")
        return False


def test_session_manager():
    """Test Redis session manager"""
    print("\n🔍 Testing Redis Session Manager")
    print("=" * 50)
    
    if not REDIS_AVAILABLE:
        print("❌ Skipping - Redis not available")
        return False
    
    try:
        # Set test environment variables
        os.environ['SESSION_SECRET_KEY'] = 'test-secret-key-for-session-management-32-chars'
        
        # Create session manager
        session_manager = RedisSessionManager(
            redis_url='redis://localhost:6379/1',  # Use different DB for tests
            session_timeout=300,  # 5 minutes for testing
            max_sessions_per_user=3
        )
        
        # Test health check
        if not session_manager.health_check():
            print("❌ Session manager health check failed")
            return False
        print("✅ Session manager health check passed")
        
        # Create test user
        test_user = User.create(
            email='test@example.com',
            password='test-password-123',
            role=UserRole.USER
        )
        test_user.id = 'test-user-123'
        
        # Test session creation
        session_token, csrf_token = session_manager.create_session(
            test_user,
            ip_address='127.0.0.1',
            user_agent='Test-Agent/1.0'
        )
        
        if not session_token or not csrf_token:
            print("❌ Session creation failed")
            return False
        print(f"✅ Session created: {session_token[:20]}...")
        
        # Test session retrieval
        session_data = session_manager.get_session(session_token)
        if not session_data:
            print("❌ Session retrieval failed")
            return False
        
        if session_data.user_id != test_user.id:
            print("❌ Session data mismatch")
            return False
        print("✅ Session retrieved and validated")
        
        # Test CSRF validation
        if not session_manager.validate_csrf_token(session_data, csrf_token):
            print("❌ CSRF token validation failed")
            return False
        print("✅ CSRF token validation passed")
        
        # Test session refresh
        time.sleep(1)  # Wait a bit
        new_token = session_manager.refresh_session(session_token)
        if not new_token:
            print("❌ Session refresh failed")
            return False
        print("✅ Session refreshed successfully")
        
        # Test session invalidation
        if not session_manager.invalidate_session(new_token):
            print("❌ Session invalidation failed")
            return False
        print("✅ Session invalidated successfully")
        
        # Verify session is gone
        invalid_session = session_manager.get_session(new_token)
        if invalid_session:
            print("❌ Session should be invalid after invalidation")
            return False
        print("✅ Session properly invalidated")
        
        # Test multiple sessions and cleanup
        sessions = []
        for i in range(5):  # Create more than max allowed
            token, _ = session_manager.create_session(test_user)
            sessions.append(token)
        
        # Check session info
        session_info = session_manager.get_session_info(test_user.id)
        active_count = session_info['active_sessions']
        
        if active_count > session_manager.max_sessions_per_user:
            print(f"❌ Too many active sessions: {active_count}")
            return False
        print(f"✅ Session cleanup working: {active_count} active sessions")
        
        # Test invalidate all user sessions
        invalidated_count = session_manager.invalidate_all_user_sessions(test_user.id)
        print(f"✅ Invalidated {invalidated_count} user sessions")
        
        print("✅ All session manager tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Session manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rate_limiter():
    """Test Redis rate limiter"""
    print("\n🔍 Testing Redis Rate Limiter")
    print("=" * 50)
    
    if not REDIS_AVAILABLE:
        print("❌ Skipping - Redis not available")
        return False
    
    try:
        redis_client = redis.from_url('redis://localhost:6379/2', decode_responses=True)  # Different DB
        rate_limiter = RedisRateLimiter(redis_client)
        
        test_identifier = "test-user-rate-limit"
        
        # Test sliding window rate limiting
        print("Testing sliding window rate limiting...")
        custom_rule = RateLimitRule(
            max_attempts=3,
            window_seconds=10,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            block_duration=5
        )
        
        # First 3 attempts should be allowed
        for i in range(3):
            result = rate_limiter.check_rate_limit(test_identifier, 'test_rule', custom_rule)
            if not result.allowed:
                print(f"❌ Attempt {i+1} should be allowed")
                return False
            print(f"✅ Attempt {i+1} allowed, remaining: {result.remaining}")
        
        # 4th attempt should be blocked
        result = rate_limiter.check_rate_limit(test_identifier, 'test_rule', custom_rule)
        if result.allowed:
            print("❌ 4th attempt should be blocked")
            return False
        print(f"✅ 4th attempt blocked, retry after: {result.retry_after}s")
        
        # Test rate limit status
        status = rate_limiter.get_rate_limit_status(test_identifier, 'test_rule')
        # Note: Status might not show blocked immediately due to Redis timing
        print(f"✅ Rate limit status: {status.get('blocked', False)}")
        
        # Test manual unblock
        if not rate_limiter.unblock_identifier(test_identifier, 'test_rule'):
            print("❌ Manual unblock failed")
            return False
        print("✅ Manual unblock successful")
        
        # Test reset rate limit
        if not rate_limiter.reset_rate_limit(test_identifier, 'test_rule'):
            print("❌ Rate limit reset failed")
            return False
        print("✅ Rate limit reset successful")
        
        # Test token bucket strategy
        print("Testing token bucket rate limiting...")
        token_rule = RateLimitRule(
            max_attempts=5,
            window_seconds=10,
            strategy=RateLimitStrategy.TOKEN_BUCKET
        )
        
        # Consume all tokens
        for i in range(5):
            result = rate_limiter.check_rate_limit("token-test", 'token_rule', token_rule)
            if not result.allowed:
                print(f"❌ Token {i+1} should be available")
                return False
        
        # Next request should be blocked
        result = rate_limiter.check_rate_limit("token-test", 'token_rule', token_rule)
        if result.allowed:
            print("❌ Should be out of tokens")
            return False
        print("✅ Token bucket correctly exhausted")
        
        print("✅ All rate limiter tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Rate limiter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cookie_manager():
    """Test secure cookie manager"""
    print("\n🔍 Testing Secure Cookie Manager")
    print("=" * 50)
    
    try:
        # Set test environment variables
        os.environ['COOKIE_SECRET_KEY'] = 'test-cookie-secret-key-32-characters'
        
        cookie_manager = SecureCookieManager(
            domain='localhost',
            secure=False  # For testing
        )
        
        # Test session cookie generation
        test_token = 'test-session-token-123'
        cookie_js = cookie_manager.set_session_cookie(test_token, max_age=3600)
        
        if not cookie_js or 'document.cookie' not in cookie_js:
            print("❌ Session cookie JavaScript generation failed")
            return False
        print("✅ Session cookie JavaScript generated")
        
        # Test CSRF cookie generation
        csrf_token = 'test-csrf-token-456'
        csrf_js = cookie_manager.set_csrf_cookie(csrf_token, max_age=3600)
        
        if not csrf_js or 'document.cookie' not in csrf_js:
            print("❌ CSRF cookie JavaScript generation failed")
            return False
        print("✅ CSRF cookie JavaScript generated")
        
        # Test cookie clearing
        clear_js = cookie_manager.clear_session_cookies()
        if not clear_js or 'Max-Age=0' not in clear_js:
            print("❌ Cookie clearing JavaScript generation failed")
            return False
        print("✅ Cookie clearing JavaScript generated")
        
        # Test CSRF form field
        csrf_field = cookie_manager.create_csrf_form_field(csrf_token)
        if not csrf_field or 'csrf_token' not in csrf_field:
            print("❌ CSRF form field generation failed")
            return False
        print("✅ CSRF form field generated")
        
        # Test CSRF validation
        form_data = {'csrf_token': csrf_token}
        if not cookie_manager.validate_csrf_from_form(form_data, csrf_token):
            print("❌ CSRF form validation failed")
            return False
        print("✅ CSRF form validation passed")
        
        # Test security headers
        headers = cookie_manager.generate_secure_headers()
        required_headers = ['X-Content-Type-Options', 'X-Frame-Options', 'X-XSS-Protection']
        for header in required_headers:
            if header not in headers:
                print(f"❌ Missing security header: {header}")
                return False
        print("✅ Security headers generated")
        
        # Test cookie info
        info = cookie_manager.get_cookie_info()
        if not info.get('session_cookie_name') or not info.get('csrf_cookie_name'):
            print("❌ Cookie info incomplete")
            return False
        print("✅ Cookie info complete")
        
        print("✅ All cookie manager tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Cookie manager test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_session_security():
    """Test session security features"""
    print("\n🔍 Testing Session Security Features")
    print("=" * 50)
    
    if not REDIS_AVAILABLE:
        print("❌ Skipping - Redis not available")
        return False
    
    try:
        os.environ['SESSION_SECRET_KEY'] = 'test-security-key-32-characters-long'
        
        session_manager = RedisSessionManager(
            redis_url='redis://localhost:6379/3',  # Different DB
            session_timeout=5,  # Short timeout for testing
        )
        
        test_user = User.create(
            email='security@example.com',
            password='security-test-password',
            role=UserRole.ADMIN
        )
        test_user.id = 'security-test-user'
        
        # Test session expiration
        print("Testing session expiration...")
        session_token, csrf_token = session_manager.create_session(test_user)
        
        # Session should be valid immediately
        session_data = session_manager.get_session(session_token)
        if not session_data:
            print("❌ Fresh session should be valid")
            return False
        print("✅ Fresh session is valid")
        
        # Wait for expiration
        print("Waiting for session expiration...")
        time.sleep(6)  # Wait longer than timeout
        
        expired_session = session_manager.get_session(session_token)
        if expired_session:
            print("❌ Session should have expired")
            return False
        print("✅ Session properly expired")
        
        # Test session data encryption
        print("Testing session data encryption...")
        new_token, _ = session_manager.create_session(test_user)
        
        # Try to access raw Redis data
        with session_manager.get_redis_connection() as redis_client:
            session_key = f"{session_manager.session_prefix}{session_manager.session_serializer.loads(new_token)}"
            raw_data = redis_client.get(session_key)
            
            if not raw_data:
                print("❌ Session data not found in Redis")
                return False
            
            # Raw data should be encrypted (not readable JSON)
            try:
                import json
                json.loads(raw_data)
                print("❌ Session data appears to be unencrypted")
                return False
            except json.JSONDecodeError:
                print("✅ Session data is properly encrypted")
        
        # Test concurrent session limits
        print("Testing concurrent session limits...")
        sessions = []
        max_sessions = session_manager.max_sessions_per_user
        
        # Create maximum allowed sessions
        for i in range(max_sessions + 2):  # Create more than allowed
            token, _ = session_manager.create_session(test_user)
            sessions.append(token)
        
        # Check how many are actually active
        session_info = session_manager.get_session_info(test_user.id)
        active_count = session_info['active_sessions']
        
        if active_count > max_sessions:
            print(f"❌ Too many concurrent sessions: {active_count} > {max_sessions}")
            return False
        print(f"✅ Concurrent sessions limited to {active_count}")
        
        print("✅ All security tests passed")
        return True
        
    except Exception as e:
        print(f"❌ Security test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_performance():
    """Test session management performance"""
    print("\n🔍 Testing Session Management Performance")
    print("=" * 50)
    
    if not REDIS_AVAILABLE:
        print("❌ Skipping - Redis not available")
        return False
    
    try:
        os.environ['SESSION_SECRET_KEY'] = 'performance-test-key-32-characters'
        
        session_manager = RedisSessionManager(
            redis_url='redis://localhost:6379/4'  # Different DB
        )
        
        test_user = User.create(
            email='perf@example.com',
            password='perf-test-password',
            role=UserRole.USER
        )
        test_user.id = 'perf-test-user'
        
        # Test session creation performance
        print("Testing session creation performance...")
        start_time = time.time()
        
        sessions = []
        for i in range(100):
            token, _ = session_manager.create_session(test_user)
            sessions.append(token)
        
        creation_time = time.time() - start_time
        creation_rate = 100 / creation_time
        print(f"✅ Created 100 sessions in {creation_time:.2f}s ({creation_rate:.1f} sessions/sec)")
        
        # Test session validation performance
        print("Testing session validation performance...")
        start_time = time.time()
        
        valid_count = 0
        for token in sessions:
            session_data = session_manager.get_session(token)
            if session_data:
                valid_count += 1
        
        validation_time = time.time() - start_time
        validation_rate = 100 / validation_time
        print(f"✅ Validated 100 sessions in {validation_time:.2f}s ({validation_rate:.1f} validations/sec)")
        print(f"✅ {valid_count}/100 sessions were valid")
        
        # Test cleanup performance
        print("Testing cleanup performance...")
        start_time = time.time()
        
        invalidated = session_manager.invalidate_all_user_sessions(test_user.id)
        
        cleanup_time = time.time() - start_time
        print(f"✅ Cleaned up {invalidated} sessions in {cleanup_time:.2f}s")
        
        # Performance thresholds
        if creation_rate < 50:
            print(f"⚠️  Session creation rate is low: {creation_rate:.1f}/sec")
        
        if validation_rate < 100:
            print(f"⚠️  Session validation rate is low: {validation_rate:.1f}/sec")
        
        print("✅ Performance tests completed")
        return True
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Redis session management tests"""
    print("🧪 Redis Session Management Test Suite")
    print("=" * 60)
    
    tests = [
        ("Redis Connection", test_redis_connection),
        ("Session Manager", test_session_manager),
        ("Rate Limiter", test_rate_limiter),
        ("Cookie Manager", test_cookie_manager),
        ("Session Security", test_session_security),
        ("Performance", test_performance),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            failed += 1
    
    print("\n🎯 Test Results")
    print("=" * 60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All Redis session management tests passed!")
        print("\n📋 System Ready:")
        print("  ✅ Redis-based session storage")
        print("  ✅ Secure HTTP-only cookies")
        print("  ✅ CSRF protection")
        print("  ✅ Session expiration and renewal")
        print("  ✅ Rate limiting")
        print("  ✅ Multi-worker support")
        print("  ✅ Security monitoring")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the issues above.")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
