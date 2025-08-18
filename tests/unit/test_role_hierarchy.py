#!/usr/bin/env python3
"""
Unit tests for role-based access control and user role hierarchy.
"""

import unittest
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.models.user import User, UserRole
from src.security.auth import RoleBasedAccessControl, Permission


class TestUserRoleHierarchy(unittest.TestCase):
    """Test user role hierarchy and permission system."""
    
    def test_role_level_hierarchy(self):
        """Test that role levels are correctly defined."""
        # Test numeric hierarchy values
        self.assertEqual(UserRole.VIEWER.level, 0)
        self.assertEqual(UserRole.USER.level, 1)
        self.assertEqual(UserRole.MANAGER.level, 2)
        self.assertEqual(UserRole.ADMIN.level, 3)
        
        # Test hierarchy ordering
        self.assertLess(UserRole.VIEWER.level, UserRole.USER.level)
        self.assertLess(UserRole.USER.level, UserRole.MANAGER.level)
        self.assertLess(UserRole.MANAGER.level, UserRole.ADMIN.level)
    
    def test_user_permission_hierarchy(self):
        """Test user permission checking with hierarchy."""
        # Create users with different roles
        admin_user = User(
            id="1", email="admin@test.com", password_hash=b"hash",
            role=UserRole.ADMIN, created_at=None, last_login=None
        )
        manager_user = User(
            id="2", email="manager@test.com", password_hash=b"hash",
            role=UserRole.MANAGER, created_at=None, last_login=None
        )
        regular_user = User(
            id="3", email="user@test.com", password_hash=b"hash",
            role=UserRole.USER, created_at=None, last_login=None
        )
        viewer_user = User(
            id="4", email="viewer@test.com", password_hash=b"hash",
            role=UserRole.VIEWER, created_at=None, last_login=None
        )
        
        # Test admin permissions
        self.assertTrue(admin_user.has_permission(UserRole.ADMIN))
        self.assertTrue(admin_user.has_permission(UserRole.MANAGER))
        self.assertTrue(admin_user.has_permission(UserRole.USER))
        self.assertTrue(admin_user.has_permission(UserRole.VIEWER))
        
        # Test manager permissions
        self.assertFalse(manager_user.has_permission(UserRole.ADMIN))
        self.assertTrue(manager_user.has_permission(UserRole.MANAGER))
        self.assertTrue(manager_user.has_permission(UserRole.USER))
        self.assertTrue(manager_user.has_permission(UserRole.VIEWER))
        
        # Test regular user permissions
        self.assertFalse(regular_user.has_permission(UserRole.ADMIN))
        self.assertFalse(regular_user.has_permission(UserRole.MANAGER))
        self.assertTrue(regular_user.has_permission(UserRole.USER))
        self.assertTrue(regular_user.has_permission(UserRole.VIEWER))
        
        # Test viewer permissions
        self.assertFalse(viewer_user.has_permission(UserRole.ADMIN))
        self.assertFalse(viewer_user.has_permission(UserRole.MANAGER))
        self.assertFalse(viewer_user.has_permission(UserRole.USER))
        self.assertTrue(viewer_user.has_permission(UserRole.VIEWER))
    
    def test_user_access_methods(self):
        """Test additional user access methods."""
        manager_user = User(
            id="1", email="manager@test.com", password_hash=b"hash",
            role=UserRole.MANAGER, created_at=None, last_login=None
        )
        
        # Test can_access_role method
        self.assertTrue(manager_user.can_access_role(UserRole.USER))
        self.assertTrue(manager_user.can_access_role(UserRole.VIEWER))
        self.assertFalse(manager_user.can_access_role(UserRole.ADMIN))
        
        # Test get_permission_level method
        self.assertEqual(manager_user.get_permission_level(), 2)
    
    def test_role_permissions_mapping(self):
        """Test that all roles have proper permission mappings."""
        rbac = RoleBasedAccessControl()
        
        # Test that all roles are defined in permissions
        self.assertIn(UserRole.ADMIN, rbac.ROLE_PERMISSIONS)
        self.assertIn(UserRole.MANAGER, rbac.ROLE_PERMISSIONS)
        self.assertIn(UserRole.USER, rbac.ROLE_PERMISSIONS)
        self.assertIn(UserRole.VIEWER, rbac.ROLE_PERMISSIONS)
        
        # Test admin has all permissions
        admin_perms = rbac.get_user_permissions(UserRole.ADMIN)
        self.assertIn(Permission.VIEW_DASHBOARD, admin_perms)
        self.assertIn(Permission.MANAGE_USERS, admin_perms)
        self.assertIn(Permission.VIEW_AUDIT_LOGS, admin_perms)
        
        # Test manager has subset of admin permissions
        manager_perms = rbac.get_user_permissions(UserRole.MANAGER)
        self.assertIn(Permission.VIEW_DASHBOARD, manager_perms)
        self.assertIn(Permission.MANAGE_COSTS, manager_perms)
        self.assertNotIn(Permission.MANAGE_USERS, manager_perms)
        self.assertNotIn(Permission.VIEW_AUDIT_LOGS, manager_perms)
        
        # Test user has basic permissions
        user_perms = rbac.get_user_permissions(UserRole.USER)
        self.assertIn(Permission.VIEW_DASHBOARD, user_perms)
        self.assertIn(Permission.MANAGE_COSTS, user_perms)
        self.assertNotIn(Permission.MANAGE_PAYMENTS, user_perms)
        self.assertNotIn(Permission.MANAGE_USERS, user_perms)
        
        # Test viewer has minimal permissions
        viewer_perms = rbac.get_user_permissions(UserRole.VIEWER)
        self.assertIn(Permission.VIEW_DASHBOARD, viewer_perms)
        self.assertIn(Permission.VIEW_ANALYTICS, viewer_perms)
        self.assertNotIn(Permission.MANAGE_COSTS, viewer_perms)
        self.assertNotIn(Permission.MANAGE_PAYMENTS, viewer_perms)
    
    def test_permission_hierarchy_consistency(self):
        """Test that permission hierarchy is consistent."""
        rbac = RoleBasedAccessControl()
        
        admin_perms = rbac.get_user_permissions(UserRole.ADMIN)
        manager_perms = rbac.get_user_permissions(UserRole.MANAGER)
        user_perms = rbac.get_user_permissions(UserRole.USER)
        viewer_perms = rbac.get_user_permissions(UserRole.VIEWER)
        
        # Higher roles should have all permissions of lower roles
        self.assertTrue(viewer_perms.issubset(user_perms))
        self.assertTrue(user_perms.issubset(manager_perms))
        self.assertTrue(manager_perms.issubset(admin_perms))
    
    def test_specific_permission_checks(self):
        """Test specific permission checks for each role."""
        rbac = RoleBasedAccessControl()
        
        # Test VIEW_DASHBOARD - all roles should have this
        self.assertTrue(rbac.has_permission(UserRole.ADMIN, Permission.VIEW_DASHBOARD))
        self.assertTrue(rbac.has_permission(UserRole.MANAGER, Permission.VIEW_DASHBOARD))
        self.assertTrue(rbac.has_permission(UserRole.USER, Permission.VIEW_DASHBOARD))
        self.assertTrue(rbac.has_permission(UserRole.VIEWER, Permission.VIEW_DASHBOARD))
        
        # Test MANAGE_COSTS - USER and above should have this
        self.assertTrue(rbac.has_permission(UserRole.ADMIN, Permission.MANAGE_COSTS))
        self.assertTrue(rbac.has_permission(UserRole.MANAGER, Permission.MANAGE_COSTS))
        self.assertTrue(rbac.has_permission(UserRole.USER, Permission.MANAGE_COSTS))
        self.assertFalse(rbac.has_permission(UserRole.VIEWER, Permission.MANAGE_COSTS))
        
        # Test MANAGE_PAYMENTS - MANAGER and above should have this
        self.assertTrue(rbac.has_permission(UserRole.ADMIN, Permission.MANAGE_PAYMENTS))
        self.assertTrue(rbac.has_permission(UserRole.MANAGER, Permission.MANAGE_PAYMENTS))
        self.assertFalse(rbac.has_permission(UserRole.USER, Permission.MANAGE_PAYMENTS))
        self.assertFalse(rbac.has_permission(UserRole.VIEWER, Permission.MANAGE_PAYMENTS))
        
        # Test MANAGE_USERS - only ADMIN should have this
        self.assertTrue(rbac.has_permission(UserRole.ADMIN, Permission.MANAGE_USERS))
        self.assertFalse(rbac.has_permission(UserRole.MANAGER, Permission.MANAGE_USERS))
        self.assertFalse(rbac.has_permission(UserRole.USER, Permission.MANAGE_USERS))
        self.assertFalse(rbac.has_permission(UserRole.VIEWER, Permission.MANAGE_USERS))
    
    def test_role_enum_string_values(self):
        """Test that role enum string values are correct."""
        self.assertEqual(UserRole.ADMIN.value, "admin")
        self.assertEqual(UserRole.MANAGER.value, "manager")
        self.assertEqual(UserRole.USER.value, "user")
        self.assertEqual(UserRole.VIEWER.value, "viewer")
    
    def test_role_creation_from_string(self):
        """Test creating UserRole from string values."""
        self.assertEqual(UserRole("admin"), UserRole.ADMIN)
        self.assertEqual(UserRole("manager"), UserRole.MANAGER)
        self.assertEqual(UserRole("user"), UserRole.USER)
        self.assertEqual(UserRole("viewer"), UserRole.VIEWER)
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        user = User(
            id="1", email="test@test.com", password_hash=b"hash",
            role=UserRole.USER, created_at=None, last_login=None
        )
        
        # Test permission check with same role
        self.assertTrue(user.has_permission(UserRole.USER))
        
        # Test with invalid role (should handle gracefully)
        rbac = RoleBasedAccessControl()
        empty_perms = rbac.get_user_permissions(None)
        self.assertEqual(empty_perms, set())


class TestRoleIntegration(unittest.TestCase):
    """Integration tests for role system."""
    
    def test_user_creation_with_roles(self):
        """Test user creation with different roles."""
        # Test default role
        user1 = User.create("test1@example.com", "password123")
        self.assertEqual(user1.role, UserRole.USER)
        
        # Test explicit roles
        admin = User.create("admin@example.com", "password123", UserRole.ADMIN)
        self.assertEqual(admin.role, UserRole.ADMIN)
        
        manager = User.create("manager@example.com", "password123", UserRole.MANAGER)
        self.assertEqual(manager.role, UserRole.MANAGER)
        
        viewer = User.create("viewer@example.com", "password123", UserRole.VIEWER)
        self.assertEqual(viewer.role, UserRole.VIEWER)
    
    def test_permission_inheritance(self):
        """Test that permission inheritance works correctly."""
        admin = User.create("admin@example.com", "password123", UserRole.ADMIN)
        manager = User.create("manager@example.com", "password123", UserRole.MANAGER)
        user = User.create("user@example.com", "password123", UserRole.USER)
        viewer = User.create("viewer@example.com", "password123", UserRole.VIEWER)
        
        # Test cascading permissions
        users = [admin, manager, user, viewer]
        
        # Everyone should be able to view dashboard
        for test_user in users:
            self.assertTrue(test_user.has_permission(UserRole.VIEWER))
        
        # USER and above should have user permissions
        for test_user in [admin, manager, user]:
            self.assertTrue(test_user.has_permission(UserRole.USER))
        self.assertFalse(viewer.has_permission(UserRole.USER))
        
        # MANAGER and above should have manager permissions
        for test_user in [admin, manager]:
            self.assertTrue(test_user.has_permission(UserRole.MANAGER))
        for test_user in [user, viewer]:
            self.assertFalse(test_user.has_permission(UserRole.MANAGER))
        
        # Only ADMIN should have admin permissions
        self.assertTrue(admin.has_permission(UserRole.ADMIN))
        for test_user in [manager, user, viewer]:
            self.assertFalse(test_user.has_permission(UserRole.ADMIN))


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)
