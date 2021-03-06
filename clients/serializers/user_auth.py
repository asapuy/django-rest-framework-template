from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from clients.models import User
from core import auth, email_helper

MESSAGES = {
    'invalid_old_password': _("Old password is invalid"),
    'password_must_be_different': _("New password must be different from old password.")
}


class AuthenticateCredentialsSerializer(serializers.Serializer):
    email = serializers.CharField(required=True, label="Email", max_length=250)
    password = serializers.CharField(required=True, label="Password", max_length=250)


class AuthenticateTokenSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, label="Token", max_length=2048)


class RequestPasswordRecoverySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, label="Email", max_length=250)

    def validate(self, data):

        user = None

        # Try to get user by email. If not found fail silently, 
        # This way we reduce user email enumerations
        try:
            user = User.objects.get(email=data['email'])
        except User.DoesNotExist:
            pass

        self.instance = user

        return data

    def save(self):
        # TODO: Translate emails and use html templates (with translations as well,
        # such as {% load i18n %} + {% trans "hello" %}

        if not self.instance:
            return

        # Create token
        token = auth.create_user_password_recovery_token(self.instance)

        email_text = auth.PASSWORD_RECOVERY_EMAIL_TEXT.format(token)
        email_html = auth.PASSWORD_RECOVERY_EMAIL_TEXT_HTML.format(token)

        email_helper.send_email(
            "Password Recovery",
            [self.instance.email],
            from_email=None,
            plain_text=email_text,
            html_text=email_html,
            async=True
        )


class PasswordChangeSerializer(serializers.Serializer):
    """
        Requires current user on context
    """

    old_password = serializers.CharField(required=True, label="Old Password", max_length=250)
    new_password = serializers.CharField(required=True, label="New Password", max_length=250)

    def validate(self, data):

        user = self.context['user']

        # validate old password
        if not auth.check_user_password(user, data['old_password']):
            raise serializers.ValidationError({'old_password': MESSAGES['invalid_old_password']})

        # Validate password
        try:
            auth.validate_user_password(user, data['new_password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({'new_password': e.messages})

        if data['old_password'] == data['new_password']:
            raise serializers.ValidationError({'new_password': MESSAGES['password_must_be_different']})

        auth.set_user_password(user, data['new_password'])

        self.instance = user

        return data

    def save(self):
        self.instance.save()
        return self.instance


class TokenPasswordChangeSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, label="Token", max_length=2048)
    password = serializers.CharField(required=True, label="Password", max_length=250)

    def validate(self, data):

        user = auth.validate_user_password_recovery_token(data['token'])

        try:
            auth.validate_user_password(user, data['password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({'password': e.messages})

        user.requires_password_change = False
        user.requires_password_change_msg = ""
        auth.set_user_password(user, data['password'])
        self.instance = user

        return data

    def save(self):

        self.instance.save()
        return self.instance
