import jwt
import requests
from django.conf import settings
from django.contrib.auth import login
from .models import User

class ClerkAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        public_paths = ['/accounts/sign-in/', '/accounts/sign-up/', '/accounts/webhook/clerk/']
        if request.path in public_paths or request.path.startswith('/admin/'):
            return self.get_response(request)
        
        session_token = request.COOKIES.get('__session')
        
        if session_token:
            try:
                jwks_client = jwt.PyJWKClient(settings.CLERK_JWKS_URL)
                signing_key = jwks_client.get_signing_key_from_jwt(session_token)
                
                payload = jwt.decode(
                    session_token,
                    signing_key.key,
                    algorithms=['RS256'],
                    audience=settings.CLERK_PUBLISHABLE_KEY
                )
                
                clerk_id = payload.get('sub')
                
                if clerk_id:
                    user, created = User.objects.get_or_create(
                        clerk_id=clerk_id,
                        defaults={
                            'email': payload.get('email', ''),
                            'username': payload.get('email', '').split('@')[0],
                            'first_name': payload.get('first_name', ''),
                            'last_name': payload.get('last_name', ''),
                        }
                    )
                    request.user = user
            except Exception as e:
                print(f"JWT validation error: {e}")
        
        return self.get_response(request)