# File: syncdata/authentication.py
# Replace the existing CustomJWTAuthentication.get_user(...) with the code below.

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings
from rest_framework.exceptions import AuthenticationFailed
from syncdata.models import AccUsers
import logging

logger = logging.getLogger(__name__)

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        """
        Resolve the user from the validated token.

        Behavior:
         - Prefer to resolve by both user_id (usual claim) AND client_id (token claim).
         - Accept common client_id claim names ('client_id', 'client', 'cid').
         - If client_id is missing, try to resolve by user_id only but fail if ambiguous.
         - Provide clear AuthenticationFailed messages (no ambiguous DB errors).
        """
        user_id = validated_token.get(api_settings.USER_ID_CLAIM)
        if not user_id:
            raise AuthenticationFailed("Invalid token: user_id missing", code="user_id_missing")

        # normalize
        user_id = str(user_id).strip()

        # try common client id claim names
        client_id = None
        for ckey in ("client_id", "client", "cid"):
            v = validated_token.get(ckey)
            if v:
                client_id = str(v).strip()
                break

        # If we have client_id, do a precise lookup by both fields
        if client_id:
            users_qs = AccUsers.objects.filter(id=user_id, client_id=client_id)
            user = users_qs.first()
            if not user:
                # explicit fail: exact pair not found
                logger.warning("Auth failed: no AccUsers row for id=%s client_id=%s", user_id, client_id)
                raise AuthenticationFailed("User not found for provided client_id", code="user_not_found_client")
            return user

        # No client_id in token: try to resolve by user_id only, but guard against duplicates
        users_qs = AccUsers.objects.filter(id=user_id)
        count = users_qs.count()
        if count == 0:
            raise AuthenticationFailed("User not found", code="user_not_found")
        if count > 1:
            # Ambiguous: multiple user rows share the same id across different clients.
            # We cannot safely pick one without client_id — force the token to include it.
            logger.error("Ambiguous AccUsers lookup: id=%s returned %d rows; client_id not provided in token", user_id, count)
            raise AuthenticationFailed(
                "Ambiguous user lookup: token must include client_id when the same username exists in multiple clients",
                code="ambiguous_user"
            )

        # exactly 1 row -> OK
        return users_qs.first()
