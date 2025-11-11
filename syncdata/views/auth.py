# auth.py
import logging

from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken

from syncdata.models import AccUsers

logger = logging.getLogger(__name__)


class LoginView(APIView):
    """
    Login view that authenticates users from acc_users and returns a JWT token,
    user_id, client_id and role. Users without a role are rejected.
    """

    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        """
        Expected JSON body:
        {
            "user_id": "<id>",
            "password": "<password>",
            "client_id": "<client id>"
        }

        Returns:
        {
            "success": True,
            "access": "<jwt>",
            "user_id": "<id>",
            "client_id": "<client id>",
            "role": "<role>"
        }
        """
        try:
            # Defensive trimming of inputs
            user_id = (request.data.get("user_id") or "").strip()
            password = (request.data.get("password") or "").strip()
            client_id = (request.data.get("client_id") or "").strip()

            if not all([user_id, password, client_id]):
                return Response({
                    "success": False,
                    "message": "user_id, password, and client_id are required."
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                # Note: AccUsers.pass_field maps to DB column 'pass'
                user = AccUsers.objects.get(id=user_id, pass_field=password, client_id=client_id)
            except AccUsers.DoesNotExist:
                logger.debug("Login failed for user_id=%s client_id=%s", user_id, client_id)
                return Response({
                    "success": False,
                    "message": "Invalid credentials."
                }, status=status.HTTP_401_UNAUTHORIZED)

            # ENFORCE: user must have a non-empty role
            if not user.role or str(user.role).strip() == "":
                logger.info("Login blocked: user %s (client %s) has no role set", user_id, client_id)
                return Response({
                    "success": False,
                    "message": "No role assigned. Contact administrator."
                }, status=status.HTTP_403_FORBIDDEN)

            # Normalize role: remove spaces, lowercase (ex: "Level 3" → "level3")
            normalized_role = str(user.role).strip().lower().replace(" ", "")

            # Create JWT and include claims
            token = AccessToken()
            token["user_id"] = str(user.id).strip()
            token["client_id"] = str(client_id).strip()
            token["role"] = normalized_role


            logger.info("Created token for %s: role=%s, client=%s", user.id, token["role"], token["client_id"])


            return Response({
                "success": True,
                "message": "Login successful",
                "access": str(token),          # <-- IMPORTANT FIX (was: token)
                "user_id": str(user.id).strip(),
                "client_id": str(user.client_id).strip(),
                "role": normalized_role        # <-- return normalized role
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            logger.exception("Unhandled exception during login: %s", exc)
            return Response({
                "success": False,
                "message": "Server error while processing login."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
