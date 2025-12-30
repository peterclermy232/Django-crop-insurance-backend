from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone

from insurance.models import User, RoleType
from insurance.serializers import UserSerializer
from insurance.serializers.auth import RegistrationSerializer


class LoginView(APIView):
    """User login endpoint that returns JWT tokens"""
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Try to get user by email OR username
            try:
                user = User.objects.get(user_email=username)
            except User.DoesNotExist:
                user = User.objects.get(user_name=username)

            # Check if password is hashed or plain text
            password_valid = False

            if user.check_password(password):
                password_valid = True
            elif user.password == password:
                password_valid = True
                user.set_password(password)
                user.save(update_fields=['password'])

            if password_valid:
                if user.user_status != 'ACTIVE':
                    return Response(
                        {'error': 'User account is inactive'},
                        status=status.HTTP_403_FORBIDDEN
                    )

                refresh = RefreshToken.for_user(user)
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])

                return Response({
                    'token': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': UserSerializer(user).data,
                    'expires_in': 3600
                }, status=status.HTTP_200_OK)
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
        except Exception as e:
            return Response(
                {'error': f'Login failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RegisterView(APIView):
    """User registration endpoint with role support"""
    permission_classes = [AllowAny]

    def post(self, request):
        """
        Register a new user with specified role
        
        Request body:
        {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "securepassword123",
            "user_phone_number": "+254700000000",
            "organisation_id": 1,
            "user_role": "AGENT"  // Optional, defaults to CUSTOMER
        }
        """
        serializer = RegistrationSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            try:
                user = serializer.save()
                
                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)

                return Response({
                    'message': 'User registered successfully',
                    'user': {
                        'user_id': user.user_id,
                        'user_name': user.user_name,
                        'user_email': user.user_email,
                        'user_role': user.user_role,
                        'user_status': user.user_status,
                        'organisation_id': user.organisation.organisation_id,
                        'organisation_name': user.organisation.organisation_name,
                    },
                    'token': str(refresh.access_token),
                    'refresh': str(refresh),
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response(
                    {'error': f'Registration failed: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(
            {'errors': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def get(self, request):
        """Get available roles for registration"""
        roles = RoleType.objects.filter(role_status='ACTIVE').values(
            'role_name', 'role_description'
        )
        
        return Response({
            'available_roles': list(roles),
            'default_role': 'CUSTOMER',
            'restricted_roles': ['SUPERUSER', 'ADMIN']  # Require admin approval
        })


class LogoutView(APIView):
    """User logout endpoint - blacklists the refresh token"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')

            if not refresh_token:
                return Response(
                    {'error': 'Refresh token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {'message': 'Logout successful'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': f'Logout failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class RefreshTokenView(APIView):
    """Refresh access token using refresh token"""
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)

            return Response({
                'token': access_token,
                'expires_in': 3600
            }, status=status.HTTP_200_OK)

        except Exception:
            return Response(
                {'error': 'Invalid or expired refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )