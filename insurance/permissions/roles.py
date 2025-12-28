"""
Role-based permission classes for the insurance application
"""
from rest_framework import permissions
from insurance.models import RoleType


class RoleBasedPermission(permissions.BasePermission):
    """
    Custom permission class that checks user role permissions.
    
    Usage in ViewSet:
        permission_classes = [IsAuthenticated, RoleBasedPermission]
        permission_resource = 'farmers'  # Define the resource name
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers have all permissions
        if hasattr(request.user, 'user_role') and request.user.user_role == 'SUPERUSER':
            return True
        
        # Get the resource being accessed
        resource = getattr(view, 'permission_resource', None)
        if not resource:
            # If no resource specified, default to allow
            return True
        
        # Get user's role permissions
        try:
            role = RoleType.objects.get(
                role_name=request.user.user_role,
                role_status='ACTIVE'
            )
            permissions_dict = role.permissions or {}
        except RoleType.DoesNotExist:
            return False
        
        # Check for "all" permission (full access)
        if permissions_dict.get('all'):
            return True
        
        # Map HTTP methods to permission actions
        action_map = {
            'GET': 'read',
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete',
        }
        
        # Get required action based on HTTP method
        required_action = action_map.get(request.method, 'read')
        
        # Check if user has permission for this resource and action
        resource_permissions = permissions_dict.get(resource, [])
        
        return required_action in resource_permissions


class CanManageUsers(permissions.BasePermission):
    """
    Permission check for user management operations.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers always have permission
        if hasattr(request.user, 'user_role') and request.user.user_role == 'SUPERUSER':
            return True
        
        # For GET requests (reading), allow managers and admins
        if request.method == 'GET':
            return hasattr(request.user, 'user_role') and request.user.user_role in ['ADMIN', 'MANAGER']
        
        # For write operations, check role permissions
        try:
            role = RoleType.objects.get(
                role_name=request.user.user_role,
                role_status='ACTIVE'
            )
            permissions_dict = role.permissions or {}
            
            action_map = {
                'GET': 'read',
                'POST': 'create',
                'PUT': 'update',
                'PATCH': 'update',
                'DELETE': 'delete',
            }
            
            required_action = action_map.get(request.method, 'read')
            user_permissions = permissions_dict.get('users', [])
            
            return required_action in user_permissions
        except RoleType.DoesNotExist:
            return False


class CanManageRoles(permissions.BasePermission):
    """
    Permission check for role management operations.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Superusers always have permission
        if hasattr(request.user, 'user_role') and request.user.user_role == 'SUPERUSER':
            return True
        
        # For GET requests (reading), allow admins
        if request.method == 'GET':
            return hasattr(request.user, 'user_role') and request.user.user_role in ['ADMIN']
        
        # For write operations, check role permissions
        try:
            role = RoleType.objects.get(
                role_name=request.user.user_role,
                role_status='ACTIVE'
            )
            permissions_dict = role.permissions or {}
            
            action_map = {
                'GET': 'read',
                'POST': 'create',
                'PUT': 'update',
                'PATCH': 'update',
                'DELETE': 'delete',
            }
            
            required_action = action_map.get(request.method, 'read')
            role_permissions = permissions_dict.get('roles', [])
            
            return required_action in role_permissions
        except RoleType.DoesNotExist:
            return False


def has_permission_for(user, resource, action):
    """
    Utility function to check if a user has permission for a specific resource and action.
    
    Args:
        user: User instance
        resource: String resource name (e.g., 'farmers', 'claims')
        action: String action (e.g., 'create', 'read', 'update', 'delete')
    
    Returns:
        Boolean indicating if user has permission
    """
    if not user or not user.is_authenticated:
        return False
    
    if hasattr(user, 'user_role') and user.user_role == 'SUPERUSER':
        return True
    
    try:
        role = RoleType.objects.get(
            role_name=user.user_role,
            role_status='ACTIVE'
        )
        permissions_dict = role.permissions or {}
        
        if permissions_dict.get('all'):
            return True
        
        resource_permissions = permissions_dict.get(resource, [])
        return action in resource_permissions
    except RoleType.DoesNotExist:
        return False