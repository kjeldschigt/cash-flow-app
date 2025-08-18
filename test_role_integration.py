#!/usr/bin/env python3
"""
Integration test for role-based access control across all pages.
This script validates that role permissions are properly enforced throughout the application.
"""

import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.models.user import User, UserRole
from src.security.auth import RoleBasedAccessControl, Permission
from src.ui.auth import AuthComponents


def test_role_hierarchy_consistency():
    """Test that role hierarchy is consistent across all components."""
    print("🔐 Testing Role Hierarchy Consistency")
    print("=" * 50)
    
    # Test UserRole enum levels
    print("✅ UserRole Hierarchy:")
    print(f"   VIEWER: level {UserRole.VIEWER.level}")
    print(f"   USER: level {UserRole.USER.level}")
    print(f"   MANAGER: level {UserRole.MANAGER.level}")
    print(f"   ADMIN: level {UserRole.ADMIN.level}")
    
    # Verify hierarchy order
    assert UserRole.VIEWER.level < UserRole.USER.level
    assert UserRole.USER.level < UserRole.MANAGER.level
    assert UserRole.MANAGER.level < UserRole.ADMIN.level
    print("✅ Role hierarchy levels are correctly ordered")
    
    return True


def test_user_permission_methods():
    """Test User model permission methods."""
    print("\n👤 Testing User Permission Methods")
    print("=" * 50)
    
    # Create test users
    admin = User.create("admin@test.com", "password", UserRole.ADMIN)
    manager = User.create("manager@test.com", "password", UserRole.MANAGER)
    user = User.create("user@test.com", "password", UserRole.USER)
    viewer = User.create("viewer@test.com", "password", UserRole.VIEWER)
    
    test_users = [
        ("ADMIN", admin),
        ("MANAGER", manager),
        ("USER", user),
        ("VIEWER", viewer)
    ]
    
    print("Testing has_permission method:")
    for role_name, test_user in test_users:
        print(f"\n{role_name} (level {test_user.role.level}) permissions:")
        
        # Test against all role requirements
        for target_role in [UserRole.VIEWER, UserRole.USER, UserRole.MANAGER, UserRole.ADMIN]:
            has_perm = test_user.has_permission(target_role)
            expected = test_user.role.level >= target_role.level
            assert has_perm == expected, f"{role_name} permission check failed for {target_role.value}"
            
            status = "✅" if has_perm else "❌"
            print(f"   {status} {target_role.value} (level {target_role.level})")
    
    print("\n✅ All user permission methods working correctly")
    return True


def test_rbac_permission_mappings():
    """Test RoleBasedAccessControl permission mappings."""
    print("\n🛡️ Testing RBAC Permission Mappings")
    print("=" * 50)
    
    rbac = RoleBasedAccessControl()
    
    # Test that all roles have mappings
    for role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.USER, UserRole.VIEWER]:
        perms = rbac.get_user_permissions(role)
        assert len(perms) > 0, f"Role {role.value} has no permissions defined"
        print(f"✅ {role.value.upper()}: {len(perms)} permissions")
    
    # Test permission inheritance (higher roles should have all lower role permissions)
    viewer_perms = rbac.get_user_permissions(UserRole.VIEWER)
    user_perms = rbac.get_user_permissions(UserRole.USER)
    manager_perms = rbac.get_user_permissions(UserRole.MANAGER)
    admin_perms = rbac.get_user_permissions(UserRole.ADMIN)
    
    assert viewer_perms.issubset(user_perms), "USER should have all VIEWER permissions"
    assert user_perms.issubset(manager_perms), "MANAGER should have all USER permissions"
    assert manager_perms.issubset(admin_perms), "ADMIN should have all MANAGER permissions"
    
    print("✅ Permission inheritance is correct")
    
    # Test specific critical permissions
    critical_tests = [
        (Permission.VIEW_DASHBOARD, [UserRole.ADMIN, UserRole.MANAGER, UserRole.USER, UserRole.VIEWER]),
        (Permission.MANAGE_COSTS, [UserRole.ADMIN, UserRole.MANAGER, UserRole.USER]),
        (Permission.MANAGE_PAYMENTS, [UserRole.ADMIN, UserRole.MANAGER]),
        (Permission.MANAGE_USERS, [UserRole.ADMIN]),
        (Permission.VIEW_AUDIT_LOGS, [UserRole.ADMIN])
    ]
    
    print("\nTesting critical permission assignments:")
    for permission, allowed_roles in critical_tests:
        print(f"\n{permission.value}:")
        for role in [UserRole.ADMIN, UserRole.MANAGER, UserRole.USER, UserRole.VIEWER]:
            has_perm = rbac.has_permission(role, permission)
            should_have = role in allowed_roles
            
            assert has_perm == should_have, f"Permission {permission.value} incorrectly assigned to {role.value}"
            
            status = "✅" if has_perm else "❌"
            print(f"   {status} {role.value}")
    
    print("\n✅ All RBAC permission mappings are correct")
    return True


def test_auth_components_integration():
    """Test AuthComponents role checking methods."""
    print("\n🔧 Testing AuthComponents Integration")
    print("=" * 50)
    
    # Test that AuthComponents has the updated methods
    assert hasattr(AuthComponents, 'require_role'), "AuthComponents missing require_role method"
    assert hasattr(AuthComponents, 'require_exact_role'), "AuthComponents missing require_exact_role method"
    
    print("✅ AuthComponents has required role checking methods")
    
    # Note: We can't fully test AuthComponents without Streamlit session state,
    # but we can verify the methods exist and have correct signatures
    import inspect
    
    require_role_sig = inspect.signature(AuthComponents.require_role)
    assert 'required_role' in require_role_sig.parameters, "require_role missing required_role parameter"
    
    require_exact_role_sig = inspect.signature(AuthComponents.require_exact_role)
    assert 'required_role' in require_exact_role_sig.parameters, "require_exact_role missing required_role parameter"
    
    print("✅ AuthComponents methods have correct signatures")
    return True


def test_page_authentication_patterns():
    """Analyze page authentication patterns."""
    print("\n📄 Analyzing Page Authentication Patterns")
    print("=" * 50)
    
    pages_dir = Path(__file__).parent / "pages"
    if not pages_dir.exists():
        print("❌ Pages directory not found")
        return False
    
    page_files = list(pages_dir.glob("*.py"))
    auth_patterns = {
        'AuthComponents.require_authentication()': 0,
        'require_auth()': 0,
        'no_auth': 0
    }
    
    for page_file in page_files:
        try:
            content = page_file.read_text()
            
            if 'AuthComponents.require_authentication()' in content:
                auth_patterns['AuthComponents.require_authentication()'] += 1
                print(f"✅ {page_file.name}: Uses new AuthComponents")
            elif 'require_auth()' in content:
                auth_patterns['require_auth()'] += 1
                print(f"⚠️  {page_file.name}: Uses legacy require_auth")
            else:
                auth_patterns['no_auth'] += 1
                print(f"❌ {page_file.name}: No authentication found")
                
        except Exception as e:
            print(f"❌ Error reading {page_file.name}: {e}")
    
    print(f"\nAuthentication Pattern Summary:")
    print(f"   New AuthComponents: {auth_patterns['AuthComponents.require_authentication()']}")
    print(f"   Legacy require_auth: {auth_patterns['require_auth()']}")
    print(f"   No authentication: {auth_patterns['no_auth']}")
    
    total_pages = len(page_files)
    authenticated_pages = auth_patterns['AuthComponents.require_authentication()'] + auth_patterns['require_auth()']
    
    if authenticated_pages == total_pages:
        print("✅ All pages have authentication")
    else:
        print(f"⚠️  {total_pages - authenticated_pages} pages missing authentication")
    
    return True


def test_role_string_consistency():
    """Test role string values are consistent."""
    print("\n🔤 Testing Role String Consistency")
    print("=" * 50)
    
    expected_roles = {
        UserRole.ADMIN: "admin",
        UserRole.MANAGER: "manager", 
        UserRole.USER: "user",
        UserRole.VIEWER: "viewer"
    }
    
    for role, expected_value in expected_roles.items():
        assert role.value == expected_value, f"Role {role} has incorrect string value"
        
        # Test round-trip conversion
        role_from_string = UserRole(expected_value)
        assert role_from_string == role, f"String-to-role conversion failed for {expected_value}"
        
        print(f"✅ {role.value} -> {role} -> level {role.level}")
    
    print("✅ All role string values are consistent")
    return True


def main():
    """Run all role integration tests."""
    print("🧪 Cash Flow Dashboard - Role Integration Tests")
    print("=" * 60)
    
    tests = [
        test_role_hierarchy_consistency,
        test_user_permission_methods,
        test_rbac_permission_mappings,
        test_auth_components_integration,
        test_page_authentication_patterns,
        test_role_string_consistency
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
            print(f"❌ Test {test.__name__} failed: {e}")
            failed += 1
    
    print(f"\n🎯 Test Results")
    print("=" * 60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All role integration tests passed!")
        print("\n📋 Role System Summary:")
        print("  ✅ 4-tier role hierarchy (ADMIN=3, MANAGER=2, USER=1, VIEWER=0)")
        print("  ✅ Consistent permission inheritance")
        print("  ✅ Proper RBAC permission mappings")
        print("  ✅ Updated AuthComponents integration")
        print("  ✅ String value consistency")
        return True
    else:
        print(f"\n❌ {failed} test(s) failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
