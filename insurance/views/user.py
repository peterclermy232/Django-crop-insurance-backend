# insurance/views/user.py
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from insurance.models import User, Organization, Country, RoleType
from insurance.serializers import (
    UserSerializer,
    OrganizationSerializer,
    CountrySerializer,
    RoleTypeSerializer,
)

from insurance.models import Notification, Message
from insurance.serializers import NotificationSerializer, MessageSerializer
from insurance.permissions import CanManageUsers


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, CanManageUsers]

    @action(detail=False, methods=['get'])
    def with_details(self, request):
        """Return users with related organizations and countries"""
        users = self.get_serializer(self.get_queryset(), many=True).data
        orgs = OrganizationSerializer(
            Organization.objects.filter(organisation_is_deleted=False),
            many=True
        ).data
        countries = CountrySerializer(
            Country.objects.filter(country_is_deleted=False),
            many=True
        ).data

        return Response({
            'usersResponse': users,
            'orgsResponse': orgs,
            'countriesResponse': countries
        })

    @action(detail=False, methods=['post'])
    def login(self, request):
        """DEPRECATED: Use /auth/login/ instead"""
        username = request.data.get('username')
        password = request.data.get('password')

        try:
            user = User.objects.get(user_email=username)
            if user.check_password(password):
                if user.user_status == 'ACTIVE':
                    refresh = RefreshToken.for_user(user)
                    return Response({
                        'token': str(refresh.access_token),
                        'refresh': str(refresh),
                        'user': self.get_serializer(user).data
                    })
                else:
                    return Response(
                        {'error': 'User account is inactive'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            else:
                return Response(
                    {'error': 'Invalid credentials'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class RoleTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing role types
    - SUPERUSER and ADMIN can manage roles
    - Other users can only view available roles
    """
    queryset = RoleType.objects.all()
    serializer_class = RoleTypeSerializer
    permission_classes = [IsAuthenticated]  # Removed CanManageRoles - using custom logic
    
    def get_permissions(self):
        """
        Custom permissions based on action
        - List/Retrieve: All authenticated users (for dropdowns)
        - Create/Update/Delete: Only SUPERUSER and ADMIN
        """
        if self.action in ['list', 'retrieve', 'available_roles']:
            return [IsAuthenticated()]
        else:
            # For create, update, delete - check role manually
            return [IsAuthenticated()]
    
    def check_management_permission(self, request):
        """Check if user can manage roles"""
        user = request.user
        if not user or not user.is_authenticated:
            return False
        
        # SUPERUSER has all permissions
        if hasattr(user, 'user_role') and user.user_role == 'SUPERUSER':
            return True
        
        # ADMIN can manage roles
        if hasattr(user, 'user_role') and user.user_role == 'ADMIN':
            return True
        
        return False
    
    def get_queryset(self):
        """Filter roles based on permissions"""
        user = self.request.user
        queryset = RoleType.objects.all().order_by('role_name')
        
        # SUPERUSER can see all roles
        if hasattr(user, 'user_role') and user.user_role == 'SUPERUSER':
            return queryset
        
        # ADMIN can see roles in their organization
        if hasattr(user, 'user_role') and user.user_role == 'ADMIN':
            return queryset.filter(organisation=user.organisation)
        
        # Others can see all roles (for dropdowns in user management)
        # But cannot edit them (checked in create/update/delete)
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Only SUPERUSER and ADMIN can create roles"""
        if not self.check_management_permission(request):
            return Response(
                {'error': 'You do not have permission to create roles'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Only SUPERUSER and ADMIN can update roles"""
        if not self.check_management_permission(request):
            return Response(
                {'error': 'You do not have permission to update roles'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        """Only SUPERUSER and ADMIN can partially update roles"""
        if not self.check_management_permission(request):
            return Response(
                {'error': 'You do not have permission to update roles'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().partial_update(request, *args, **kwargs)
    
    def perform_create(self, serializer):
        """Set organization and added_by when creating role"""
        serializer.save(
            organisation=self.request.user.organisation,
            added_by=self.request.user.user_id
        )
    
    def perform_update(self, serializer):
        """Track who modified the role"""
        serializer.save(modified_by=self.request.user.user_id)
    
    def destroy(self, request, *args, **kwargs):
        """Only SUPERUSER and ADMIN can delete roles"""
        if not self.check_management_permission(request):
            return Response(
                {'error': 'You do not have permission to delete roles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        instance = self.get_object()
        
        # Prevent deletion of system roles
        if instance.is_system_role:
            return Response(
                {'error': 'System roles cannot be deleted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if any users have this role
        user_count = User.objects.filter(user_role=instance.role_name).count()
        if user_count > 0:
            return Response(
                {'error': f'Cannot delete role. {user_count} user(s) have this role.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=False, methods=['get'])
    def system_roles(self, request):
        """Get all system roles - available to all authenticated users"""
        roles = self.get_queryset().filter(is_system_role=True)
        serializer = self.get_serializer(roles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def custom_roles(self, request):
        """Get all custom roles - available to all authenticated users"""
        roles = self.get_queryset().filter(is_system_role=False)
        serializer = self.get_serializer(roles, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def available_roles(self, request):
        """Get list of available role names for dropdown - available to all"""
        roles = self.get_queryset().filter(role_status='ACTIVE')
        role_names = roles.values_list('role_name', flat=True)
        return Response(list(role_names))


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        from django.db.models import Q
        return Message.objects.filter(
            Q(sender=self.request.user) | Q(recipient=self.request.user)
        )