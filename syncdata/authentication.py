from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings
from rest_framework.exceptions import AuthenticationFailed
from syncdata.models import AccUsers

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user_id = validated_token.get(api_settings.USER_ID_CLAIM)

        if not user_id:
            raise AuthenticationFailed("Invalid token: user_id missing", code="user_id_missing")

        user_id = user_id.strip()

        try:
            user = AccUsers.objects.get(id=user_id)
        except AccUsers.DoesNotExist:
            raise AuthenticationFailed("User not found", code="user_not_found")

        return user
