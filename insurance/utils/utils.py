from rest_framework.views import exception_handler
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides more detailed error responses.
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        # Add custom error formatting
        custom_response_data = {
            'error': True,
            'message': str(exc),
            'status_code': response.status_code,
        }
        
        # Add field errors if available
        if hasattr(exc, 'detail'):
            custom_response_data['details'] = exc.detail
        
        # Log permission denied errors
        if response.status_code == 403:
            request = context.get('request')
            user = getattr(request, 'user', None)
            logger.warning(
                f"Permission denied: {user.user_email if user and hasattr(user, 'user_email') else 'Anonymous'} "
                f"tried to access {request.path if request else 'unknown'} with method {request.method if request else 'unknown'}"
            )
        
        response.data = custom_response_data
    
    return response


def get_user_permissions(user):
    """
    Get all permissions for a user based on their role.
    
    Returns:
        dict: Permission dictionary
    """
    from insurance.models import RoleType
    
    if not user or not user.is_authenticated:
        return {}
    
    if hasattr(user, 'user_role') and user.user_role == 'SUPERUSER':
        return {'all': True}
    
    try:
        role = RoleType.objects.get(
            role_name=user.user_role,
            role_status='ACTIVE'
        )
        return role.permissions or {}
    except RoleType.DoesNotExist:
        return {}


def check_permission(user, resource, action):
    """
    Check if user has permission for specific resource and action.
    
    Args:
        user: User instance
        resource: Resource name (e.g., 'farmers', 'claims')
        action: Action name (e.g., 'create', 'read', 'update', 'delete')
    
    Returns:
        bool: True if user has permission
    """
    permissions = get_user_permissions(user)
    
    if permissions.get('all'):
        return True
    
    resource_permissions = permissions.get(resource, [])
    return action in resource_permissions


def has_permission_for(user, resource, action):
    """
    Utility function to check if a user has permission for a specific resource and action.
    Alias for check_permission for backward compatibility.
    
    Args:
        user: User instance
        resource: String resource name (e.g., 'farmers', 'claims')
        action: String action (e.g., 'create', 'read', 'update', 'delete')
    
    Returns:
        Boolean indicating if user has permission
    """
    return check_permission(user, resource, action)


def create_notification(user, notification_type, title, message, link=None):
    """
    Create a notification for a user.
    
    Args:
        user: User instance
        notification_type: Type of notification (INFO, WARNING, SUCCESS, DANGER)
        title: Notification title
        message: Notification message
        link: Optional link
    
    Returns:
        Notification instance
    """
    from insurance.models import Notification
    
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link
    )
    
    return notification


def send_message(sender, recipient, subject, text, parent_message=None):
    """
    Send a message from one user to another.
    
    Args:
        sender: User instance (sender)
        recipient: User instance (recipient)
        subject: Message subject
        text: Message text
        parent_message: Optional parent message for replies
    
    Returns:
        Message instance
    """
    from insurance.models import Message
    
    if sender == recipient:
        raise ValueError('Cannot send message to yourself')
    
    message = Message.objects.create(
        sender=sender,
        recipient=recipient,
        subject=subject,
        text=text,
        parent_message=parent_message
    )
    
    # Create notification for recipient
    create_notification(
        user=recipient,
        notification_type='INFO',
        title='New Message',
        message=f'You have a new message from {sender.user_name}',
        link=f'/messages/{message.message_id}'
    )
    
    return message