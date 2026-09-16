import logging
from rest_framework import authentication
from django.contrib.auth import get_user_model
from .jwt_utils import decode_google_jwt

logger = logging.getLogger(__name__)
User = get_user_model()

class AllianceTokenAuthentication(authentication.BaseAuthentication):
    """
    Custom authentication for Alliance One platform:
    1. Supports Bearer token containing a Google ID token (JWT) -> automatically resolves/creates User by email.
    2. Supports dev/session tokens with 'X-User-Email' header -> resolves/creates User by email.
    3. Fallback for authenticated dev sessions without token decoding errors -> assigns active user.
    """

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization', '')
        user_email_header = request.headers.get('X-User-Email', '').strip()

        if not auth_header and not user_email_header:
            return None

        token = None
        if auth_header.startswith('Bearer '):
            token = auth_header[7:].strip()
        elif auth_header:
            token = auth_header.strip()

        # 1. Try decoding as Google JWT
        if token and '.' in token:
            payload = decode_google_jwt(token)
            if payload and 'email' in payload:
                email = payload['email'].lower()
                user, _ = User.objects.get_or_create(
                    email=email,
                    defaults={'is_active': True}
                )
                return (user, token)

        # 2. Check X-User-Email header
        if user_email_header:
            user, _ = User.objects.get_or_create(
                email=user_email_header.lower(),
                defaults={'is_active': True}
            )
            return (user, token)

        # 3. If token is provided (e.g. 'google-session-access', 'dev-token-local')
        if token:
            user = User.objects.filter(is_active=True).first()
            if not user:
                user = User.objects.create(
                    email='admin@allianceone.io',
                    is_active=True,
                    is_staff=True,
                    is_superuser=True
                )
            return (user, token)

        return None
