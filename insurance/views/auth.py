from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone

from insurance.models import User
from insurance.serializers import UserSerializer


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
    """User registration endpoint"""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('user_email')
        password = request.data.get('password')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        phone = request.data.get('user_phone_number')
        organisation_id = request.data.get('organisation_id')

        if not all([email, password, first_name, last_name]):
            return Response(
                {'error': 'Email, password, first name, and last name are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(user_email=email).exists():
            return Response(
                {'error': 'User with this email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.create(
                user_email=email,
                first_name=first_name,
                last_name=last_name,
                user_phone_number=phone,
                organisation_id=organisation_id,
                user_status='ACTIVE',
                user_role='USER',
                user_is_active=True
            )

            user.set_password(password)
            user.save()

            refresh = RefreshToken.for_user(user)

            return Response({
                'message': 'User registered successfully',
                'token': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'Registration failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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