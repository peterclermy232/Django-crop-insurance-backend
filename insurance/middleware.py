from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from insurance.models import RoleType


class RolePermissionMiddleware(MiddlewareMixin):
    """
    Middleware to add role permissions to request.
    """
    
    def process_request(self, request):
        # Skip for unauthenticated users
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        # Add role permissions to request for easy access
        try:
            role = RoleType.objects.get(
                role_name=request.user.user_role,
                role_status='ACTIVE'
            )
            request.user_permissions = role.permissions or {}
            request.is_superuser_role = (request.user.user_role == 'SUPERUSER')
        except RoleType.DoesNotExist:
            request.user_permissions = {}
            request.is_superuser_role = False
        
        return None


class AccountStatusMiddleware(MiddlewareMixin):
    """
    Middleware to check if user account is active and not locked.
    """
    
    EXEMPT_PATHS = [
        '/api/auth/login/',
        '/api/auth/logout/',
        '/api/auth/refresh/',
        '/api/users/login/',
        '/admin/',
    ]
    
    def process_request(self, request):
        # Skip for exempt paths
        if any(request.path.startswith(path) for path in self.EXEMPT_PATHS):
            return None
        
        # Skip for unauthenticated users
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return None
        
        # Check if user is active
        if hasattr(request.user, 'user_status') and request.user.user_status != 'ACTIVE':
            return JsonResponse(
                {'error': 'Your account is inactive. Please contact administrator.'},
                status=403
            )
        
        # Check if account is locked
        if hasattr(request.user, 'locked_till_date_time') and request.user.locked_till_date_time:
            from django.utils import timezone
            if request.user.locked_till_date_time > timezone.now():
                return JsonResponse(
                    {
                        'error': 'Your account is temporarily locked due to multiple failed login attempts.',
                        'locked_until': request.user.locked_till_date_time.isoformat()
                    },
                    status=403
                )
        
        return None