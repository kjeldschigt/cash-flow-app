"""
Demo script for the Smart API Key Fallback System

This demonstrates the hierarchical API key resolution:
1. Database (UI) → 2. Environment Variables → 3. Streamlit Secrets
"""

import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def demo_environment_fallback():
    """Demonstrate environment variable fallback"""
    print("🌍 Environment Variable Fallback Demo")
    print("=" * 50)
    
    # Set up test environment variables
    test_keys = {
        'STRIPE_SECRET_KEY': 'sk_test_demo_environment_stripe_key_12345',
        'OPENAI_API_KEY': 'sk-demo_environment_openai_key_67890',
        'AIRTABLE_API_KEY': 'keydemo_environment_airtable_key_abcdef'
    }
    
    # Set environment variables
    for key, value in test_keys.items():
        os.environ[key] = value
        print(f"✅ Set {key}")
    
    try:
        from src.services.api_key_resolver import APIKeyResolver, APIKeySource
        
        resolver = APIKeyResolver("demo_session", 1)
        
        # Test each service
        services = ['stripe', 'openai', 'airtable']
        
        for service in services:
            print(f"\n🔍 Testing {service.title()} service:")
            resolved = resolver.resolve_api_key(f"{service}_api_key", service, use_cache=False)
            
            if resolved.is_valid:
                print(f"  ✅ Found: {resolved.masked_value}")
                print(f"  📍 Source: {resolved.source.value}")
            else:
                print(f"  ❌ Not found: {resolved.error_message}")
        
        print(f"\n📊 Cache Status:")
        cache = resolver._get_cache()
        print(f"  Cached entries: {len(cache)}")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
    finally:
        # Clean up environment variables
        for key in test_keys.keys():
            if key in os.environ:
                del os.environ[key]
        print(f"\n🧹 Cleaned up environment variables")

def demo_priority_system():
    """Demonstrate the priority system with multiple sources"""
    print("\n\n🎯 Priority System Demo")
    print("=" * 50)
    
    # Set up environment variable (lower priority)
    os.environ['STRIPE_SECRET_KEY'] = 'sk_test_environment_priority_demo'
    
    try:
        from src.services.api_key_resolver import APIKeyResolver, APIKeySource
        
        resolver = APIKeyResolver("priority_demo_session", 1)
        
        print("🔍 Testing priority with environment variable only:")
        resolved = resolver.resolve_api_key("stripe_api_key", "stripe", use_cache=False)
        
        if resolved.is_valid:
            print(f"  ✅ Found: {resolved.masked_value}")
            print(f"  📍 Source: {resolved.source.value} (Environment)")
            print(f"  🏆 Priority: 2nd (fallback)")
        
        # Demonstrate what would happen with database priority
        print(f"\n💡 If a database key existed, it would override the environment variable")
        print(f"   Database (1st) → Environment (2nd) → Streamlit Secrets (3rd)")
        
    except Exception as e:
        print(f"❌ Priority demo failed: {e}")
    finally:
        if 'STRIPE_SECRET_KEY' in os.environ:
            del os.environ['STRIPE_SECRET_KEY']

def demo_service_status():
    """Demonstrate service status checking"""
    print("\n\n📋 Service Status Demo")
    print("=" * 50)
    
    # Set up some test keys
    test_env = {
        'STRIPE_SECRET_KEY': 'sk_test_status_demo_stripe',
        'OPENAI_API_KEY': 'sk-status_demo_openai'
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
    
    try:
        from src.services.api_key_resolver import APIKeyResolver
        
        resolver = APIKeyResolver("status_demo_session", 1)
        
        # Get all resolved keys
        all_keys = resolver.get_all_resolved_keys()
        
        print("🔌 Service Integration Status:")
        for service, resolved_key in all_keys.items():
            status_icon = "✅" if resolved_key.is_valid else "❌"
            source_info = resolved_key.source.value if resolved_key.is_valid else "not_found"
            masked_key = resolved_key.masked_value if resolved_key.is_valid else "N/A"
            
            print(f"  {status_icon} {service.title():<12} | {source_info:<15} | {masked_key}")
        
        # Show source breakdown
        configured_services = [k for k in all_keys.values() if k.is_valid]
        if configured_services:
            print(f"\n📊 Source Breakdown:")
            source_counts = {}
            for resolved in configured_services:
                source = resolved.source.value
                source_counts[source] = source_counts.get(source, 0) + 1
            
            for source, count in source_counts.items():
                print(f"  {source}: {count} service(s)")
        
    except Exception as e:
        print(f"❌ Status demo failed: {e}")
    finally:
        for key in test_env.keys():
            if key in os.environ:
                del os.environ[key]

def demo_cache_management():
    """Demonstrate cache management"""
    print("\n\n💾 Cache Management Demo")
    print("=" * 50)
    
    os.environ['STRIPE_SECRET_KEY'] = 'sk_test_cache_demo_key'
    
    try:
        from src.services.api_key_resolver import APIKeyResolver
        
        resolver = APIKeyResolver("cache_demo_session", 1)
        
        print("🔍 First resolution (will cache):")
        resolved1 = resolver.resolve_api_key("stripe_api_key", "stripe", use_cache=True)
        print(f"  Result: {resolved1.masked_value} from {resolved1.source.value}")
        
        cache = resolver._get_cache()
        print(f"  Cache entries: {len(cache)}")
        
        print(f"\n🔍 Second resolution (from cache):")
        resolved2 = resolver.resolve_api_key("stripe_api_key", "stripe", use_cache=True)
        print(f"  Result: {resolved2.masked_value} from {resolved2.source.value}")
        print(f"  Cache entries: {len(cache)}")
        
        print(f"\n🧹 Cache invalidation:")
        resolver.invalidate_cache("stripe_api_key", "stripe")
        cache_after = resolver._get_cache()
        print(f"  Cache entries after invalidation: {len(cache_after)}")
        
    except Exception as e:
        print(f"❌ Cache demo failed: {e}")
    finally:
        if 'STRIPE_SECRET_KEY' in os.environ:
            del os.environ['STRIPE_SECRET_KEY']

def demo_configuration_summary():
    """Demonstrate configuration summary"""
    print("\n\n📈 Configuration Summary Demo")
    print("=" * 50)
    
    # Set up mixed environment
    mixed_env = {
        'STRIPE_SECRET_KEY': 'sk_test_summary_stripe',
        'OPENAI_API_KEY': 'sk-summary_openai',
        'SENDGRID_API_KEY': 'SG.summary_sendgrid_key'
    }
    
    for key, value in mixed_env.items():
        os.environ[key] = value
    
    try:
        from src.services.api_key_resolver import APIKeyResolver
        
        resolver = APIKeyResolver("summary_demo_session", 1)
        
        # Get priority info
        priority_info = resolver.get_source_priority_info()
        
        print("🎯 Source Priority Order:")
        for i, source_info in enumerate(priority_info["priority_order"], 1):
            print(f"  {i}. {source_info['source']}: {source_info['description']}")
        
        print(f"\n🔧 Supported Services: {len(priority_info['supported_services'])}")
        for service in priority_info['supported_services'][:5]:  # Show first 5
            env_vars = priority_info['environment_mappings'].get(service, [])
            print(f"  • {service}: {env_vars[0] if env_vars else 'N/A'}")
        
        print(f"\n📊 Current Configuration:")
        all_keys = resolver.get_all_resolved_keys()
        configured = sum(1 for k in all_keys.values() if k.is_valid)
        total = len(all_keys)
        print(f"  Configured: {configured}/{total} services")
        
    except Exception as e:
        print(f"❌ Summary demo failed: {e}")
    finally:
        for key in mixed_env.keys():
            if key in os.environ:
                del os.environ[key]

def main():
    """Run all demos"""
    print("🚀 Smart API Key Fallback System Demo")
    print("=" * 60)
    print("This demo shows the hierarchical API key resolution system:")
    print("1. Database (UI Settings) - Highest Priority")
    print("2. Environment Variables - Fallback")  
    print("3. Streamlit Secrets - Platform Fallback")
    print("=" * 60)
    
    try:
        demo_environment_fallback()
        demo_priority_system()
        demo_service_status()
        demo_cache_management()
        demo_configuration_summary()
        
        print("\n\n🎉 Demo Complete!")
        print("\n📋 Key Features Demonstrated:")
        print("✅ Environment variable fallback detection")
        print("✅ Priority-based source resolution")
        print("✅ Service status monitoring")
        print("✅ Session-based caching with invalidation")
        print("✅ Configuration summary and analytics")
        print("✅ Secure key masking for display")
        
        print("\n💡 Next Steps:")
        print("• Set API keys through the Settings UI (highest priority)")
        print("• Use environment variables for development")
        print("• Configure Streamlit secrets for cloud deployment")
        print("• Monitor service status in the enhanced UI")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
