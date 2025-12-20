from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from insurance.models import User, RoleType, Notification, Message
from django.db.models import Q


class UserDetailSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(
        source='organisation.organisation_name',
        read_only=True
    )
    country_name = serializers.CharField(
        source='country.country',
        read_only=True
    )

    class Meta:
        model = User
        fields = [
            'user_id', 'user_name', 'user_email', 'user_phone_number',
            'user_role', 'user_status', 'organisation_name',
            'country_name', 'date_time_added'
        ]
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(
        source='organisation.organisation_name',
        read_only=True
    )
    country_name = serializers.CharField(
        source='country.country',
        read_only=True
    )
    new_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = '__all__'
        extra_kwargs = {
            'user_password': {'write_only': True}
        }

    def create(self, validated_data):
        new_password = validated_data.pop('new_password', None)
        if new_password:
            validated_data['user_password'] = make_password(new_password)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        new_password = validated_data.pop('new_password', None)
        if new_password:
            validated_data['user_password'] = make_password(new_password)
        return super().update(instance, validated_data)


class RoleTypeSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(
        source='organisation.organisation_name',
        read_only=True
    )
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = RoleType
        fields = '__all__'
        read_only_fields = ('role_id', 'date_time_added', 'date_time_modified')

    def get_user_count(self, obj):
        """Return count of users with this role"""
        return User.objects.filter(user_role=obj.role_name).count()

    def validate_role_name(self, value):
        """Validate role name uniqueness"""
        if self.instance:
            if RoleType.objects.filter(role_name=value).exclude(
                role_id=self.instance.role_id
            ).exists():
                raise serializers.ValidationError('A role with this name already exists')
        else:
            if RoleType.objects.filter(role_name=value).exists():
                raise serializers.ValidationError('A role with this name already exists')
        return value.upper()

    def validate(self, data):
        """Prevent modification of system roles"""
        if self.instance and self.instance.is_system_role:
            allowed_fields = {'role_status', 'role_description'}
            changed_fields = set(data.keys())
            if not changed_fields.issubset(allowed_fields):
                raise serializers.ValidationError(
                    'System roles can only have their status and description modified'
                )
        return data


class NotificationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.user_name', read_only=True)
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'notification_id', 'user', 'user_name', 'notification_type',
            'title', 'message', 'link', 'is_read', 'created_at',
            'read_at', 'time_ago'
        ]
        read_only_fields = ['notification_id', 'created_at', 'read_at']

    def get_time_ago(self, obj):
        """Get human-readable time difference"""
        from django.utils.timesince import timesince
        return timesince(obj.created_at) + ' ago'


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.user_name', read_only=True)
    sender_email = serializers.CharField(source='sender.user_email', read_only=True)
    recipient_name = serializers.CharField(source='recipient.user_name', read_only=True)
    recipient_email = serializers.CharField(source='recipient.user_email', read_only=True)
    time_ago = serializers.SerializerMethodField()
    has_replies = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'message_id', 'sender', 'sender_name', 'sender_email',
            'recipient', 'recipient_name', 'recipient_email',
            'subject', 'text', 'is_read', 'created_at', 'read_at',
            'parent_message', 'time_ago', 'has_replies'
        ]
        read_only_fields = ['message_id', 'created_at', 'read_at']

    def get_time_ago(self, obj):
        """Get human-readable time difference"""
        from django.utils.timesince import timesince
        return timesince(obj.created_at) + ' ago'

    def get_has_replies(self, obj):
        """Check if message has replies"""
        return obj.replies.exists()

    def validate(self, data):
        """Validate message data"""
        if data.get('sender') == data.get('recipient'):
            raise serializers.ValidationError('Cannot send message to yourself')
        return data