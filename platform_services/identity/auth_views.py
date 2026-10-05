from rest_framework.views import APIView
from rest_framework.response import Response
import requests
from django.contrib.auth import authenticate
from .models import User, Organization, OrganizationProfile, Membership
from .jwt_utils import decode_google_jwt
from django.core.mail import send_mail
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.conf import settings
from django.urls import reverse

def get_professional_email_html(magic_link, action):
    return f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 0; color: #0f172a; }}
        .container {{ max-width: 600px; margin: 40px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); border: 1px solid #e2e8f0; }}
        .header {{ background-color: #0f172a; padding: 32px 40px; text-align: center; }}
        .header h1 {{ color: #ffffff; margin: 0; font-size: 24px; font-weight: 600; font-family: 'Playfair Display', serif; letter-spacing: 1px; }}
        .hero-image {{ width: 100%; height: 240px; object-fit: cover; display: block; border-bottom: 1px solid #e2e8f0; }}
        .content {{ padding: 40px; text-align: left; }}
        .content h2 {{ margin-top: 0; font-size: 20px; font-weight: 600; color: #1e293b; }}
        .content p {{ font-size: 16px; line-height: 1.6; color: #475569; margin-bottom: 24px; }}
        .button-container {{ text-align: center; margin: 32px 0; }}
        .button {{ display: inline-block; background-color: #0f172a; color: #ffffff !important; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-weight: 600; font-size: 16px; }}
        .features {{ background-color: #f8fafc; padding: 24px; border-radius: 8px; margin-top: 32px; border: 1px solid #e2e8f0; }}
        .features h3 {{ margin-top: 0; font-size: 12px; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-bottom: 16px; }}
        .feature-item {{ margin-bottom: 12px; font-size: 14px; color: #334155; }}
        .feature-item strong {{ color: #0f172a; }}
        .footer {{ padding: 32px 40px; text-align: center; background-color: #ffffff; border-top: 1px solid #e2e8f0; }}
        .footer p {{ margin: 0; font-size: 12px; color: #94a3b8; line-height: 1.5; }}
    </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Alliance One</h1>
            </div>
            <img src="https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&q=80&w=1200" alt="Espace de travail Alliance One" class="hero-image" />
            <div class="content">
                <h2>Vérification de sécurité</h2>
                <p>Bonjour,</p>
                <p>Une demande de <strong>{action}</strong> a été initiée pour votre compte sur <strong>Alliance One</strong>, la plateforme d'excellence pour la gestion et la collaboration de votre organisation.</p>
                
                <div class="button-container">
                    <a href="{magic_link}" class="button">Confirmer mon accès</a>
                </div>
                
                <p style="font-size: 13px; color: #64748b;">Si le bouton ne fonctionne pas, copiez-collez ce lien dans votre navigateur :<br><a href="{magic_link}" style="color: #4f46e5; word-break: break-all;">{magic_link}</a></p>
                
                <div class="features">
                    <h3>Votre espace d'excellence comprend :</h3>
                    <div class="feature-item">✓ <strong>Gestion intelligente</strong> - Pilotez vos projets avec précision.</div>
                    <div class="feature-item">✓ <strong>Collaboration fluide</strong> - Connectez vos équipes en temps réel.</div>
                    <div class="feature-item">✓ <strong>Sécurité maximale</strong> - Vos données sont protégées par des standards stricts.</div>
                </div>
            </div>
            <div class="footer">
                <p>Si vous n'êtes pas à l'origine de cette demande, vous pouvez ignorer cet e-mail en toute sécurité.</p>
                <p>&copy; 2026 Alliance One. Tous droits réservés.</p>
            </div>
        </div>
    </body>
    </html>
    """


class SimpleLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response({"detail": "Email requis"}, status=400)

        user = User.objects.filter(email=email).first()
        if user is not None:
            signer = TimestampSigner()
            token = signer.sign(str(user.id))
            
            magic_link = f"http://localhost:5173/auth?token={token}"
            html_message = get_professional_email_html(magic_link, "connexion")
            
            try:
                send_mail(
                    'Connexion à votre espace - Alliance One',
                    f'Cliquez sur ce lien pour vous connecter : {magic_link}',
                    'Alliance One <benjaminadzessa@gmail.com>',
                    [user.email],
                    fail_silently=False,
                    html_message=html_message
                )
            except Exception as e:
                print('Erreur envoi email:', str(e))
                pass

            return Response({"requires_2fa": True})
        else:
            return Response({"detail": "Aucun compte trouvé avec cet email"}, status=401)

class Verify2FAView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'detail': 'Token manquant'}, status=400)
            
        signer = TimestampSigner()
        try:
            user_id = signer.unsign(token, max_age=900)
            user = User.objects.get(id=user_id)
        except (BadSignature, SignatureExpired, User.DoesNotExist):
            return Response({'detail': 'Lien expiré ou invalide'}, status=400)

        onboarding_completed = False
        membership = Membership.objects.filter(user=user).select_related('organization').first()
        if membership:
            profile = OrganizationProfile.objects.filter(organization=membership.organization).first()
            if profile and profile.onboarding_completed:
                onboarding_completed = True

        first_name = "Admin"
        last_name = "Alliance"
        if hasattr(user, 'person') and user.person:
            first_name = user.person.first_name
            last_name = user.person.last_name
        elif user.email:
            first_name = user.email.split('@')[0].capitalize()

        is_hyperadmin = False
        roles = ["ADMINISTRATOR"]
        if user.is_superuser or user.is_staff:
            is_hyperadmin = True
            roles = ["HYPERADMIN", "ADMINISTRATOR"]
        else:
            for m in Membership.objects.filter(user=user).select_related('role'):
                if m.role.name.upper() == 'HYPERADMIN':
                    is_hyperadmin = True
                    roles = ["HYPERADMIN", "ADMINISTRATOR"]
                    break

        if is_hyperadmin:
            onboarding_completed = True

        return Response({
            "access": "dev-token-local",
            "refresh": "dev-refresh-local",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": first_name,
                "last_name": last_name,
                "roles": roles,
                "is_hyperadmin": is_hyperadmin,
                "permissions": ["*"],
                "onboarding_completed": onboarding_completed,
            }
        })


class GoogleAuthView(APIView):
    """
    Point de terminaison OAuth Google.
    POST /api/core/auth/google/
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        credential = request.data.get('credential')
        if not credential:
            return Response({"detail": "Token Google manquant"}, status=400)

        payload = decode_google_jwt(credential)
        if not payload or 'email' not in payload:
            return Response({"detail": "Token Google invalide"}, status=400)

        email = payload['email'].lower()
        first_name = (
            payload.get('given_name')
            or payload.get('name', '').split(' ')[0]
            or email.split('@')[0].capitalize()
        )
        last_name = payload.get('family_name') or 'Google'

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "is_active": True,
            }
        )

        # Vérifier si l'utilisateur possède déjà une organisation ayant complété l'onboarding
        onboarding_completed = False
        membership = Membership.objects.filter(user=user).select_related('organization').first()
        if membership:
            profile = OrganizationProfile.objects.filter(organization=membership.organization).first()
            if profile and profile.onboarding_completed:
                onboarding_completed = True

        return Response({
            "access": "google-session-access",
            "refresh": "google-session-refresh",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": first_name,
                "last_name": last_name,
                "roles": ["ADMINISTRATOR"],
                "permissions": ["*"],
                "onboarding_completed": onboarding_completed,
            }
        })


class RegisterView(APIView):
    """
    Création de compte classique.
    POST /api/core/auth/register/
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        email = request.data.get('email')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')

        if not email:
            return Response({"detail": "Email requis"}, status=400)

        email = email.lower()
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"is_active": True}
        )
        if created:
            user.set_unusable_password()
            user.save()

        signer = TimestampSigner()
        token = signer.sign(str(user.id))
        
        magic_link = f"http://localhost:5173/auth?token={token}"
        html_message = get_professional_email_html(magic_link, "création de compte")
        
        try:
            send_mail(
                'Confirmez votre inscription - Alliance One',
                f'Cliquez sur ce lien pour vous connecter : {magic_link}',
                'Alliance One <benjaminadzessa@gmail.com>',
                [user.email],
                fail_silently=False,
                html_message=html_message
            )
        except Exception as e:
            print('Erreur envoi email:', str(e))
            pass

        return Response({"requires_2fa": True})

class GithubAuthView(APIView):
    """
    Point de terminaison OAuth Github.
    POST /api/core/auth/github/
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        code = request.data.get('code')
        if not code:
            return Response({"detail": "Code GitHub manquant"}, status=400)

        client_id = 'Ov23lia1vLDgsnmCaQOY'
        client_secret = '5135544e13c23dacc93273a2988561d90b66803e'

        # Exchange code for token
        token_response = requests.post(
            'https://github.com/login/oauth/access_token',
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'code': code,
            },
            headers={'Accept': 'application/json'}
        )
        
        if not token_response.ok:
            return Response({"detail": "Échec de l'authentification GitHub"}, status=400)

        token_data = token_response.json()
        access_token = token_data.get('access_token')

        if not access_token:
            return Response({"detail": "Impossible d'obtenir le token GitHub"}, status=400)

        # Get user info
        user_response = requests.get(
            'https://api.github.com/user',
            headers={'Authorization': f'Bearer {access_token}'}
        )
        if not user_response.ok:
            return Response({"detail": "Impossible de récupérer le profil GitHub"}, status=400)

        github_user = user_response.json()
        email = github_user.get('email')

        # If email is private, we need to fetch it from /user/emails
        if not email:
            emails_response = requests.get(
                'https://api.github.com/user/emails',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            if emails_response.ok:
                emails = emails_response.json()
                primary_email = next((e for e in emails if e.get('primary')), None)
                if primary_email:
                    email = primary_email.get('email')
                elif emails:
                    email = emails[0].get('email')
        
        if not email:
            return Response({"detail": "Aucun email trouvé sur ce compte GitHub"}, status=400)

        email = email.lower()
        name_parts = github_user.get('name', '').split(' ')
        first_name = name_parts[0] if name_parts and name_parts[0] else github_user.get('login', '')
        last_name = name_parts[1] if len(name_parts) > 1 else 'GitHub'

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "is_active": True,
            }
        )

        is_hyperadmin = False
        roles = ["ADMINISTRATOR"]
        if user.is_superuser or user.is_staff:
            is_hyperadmin = True
            roles = ["HYPERADMIN", "ADMINISTRATOR"]
        else:
            for m in Membership.objects.filter(user=user).select_related('role'):
                if m.role and m.role.name.upper() == 'HYPERADMIN':
                    is_hyperadmin = True
                    roles = ["HYPERADMIN", "ADMINISTRATOR"]
                    break

        onboarding_completed = True

        return Response({
            "access": "github-session-access",
            "refresh": "github-session-refresh",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": first_name,
                "last_name": last_name,
                "roles": roles,
                "is_hyperadmin": is_hyperadmin,
                "permissions": ["*"],
                "onboarding_completed": onboarding_completed,
            }
        })

