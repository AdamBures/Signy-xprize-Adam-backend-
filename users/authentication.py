from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

class BearerTokenAuthentication(TokenAuthentication):
    keyword = 'Bearer'

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
        except model.DoesNotExist:
            # If token key is invalid or demo-token, return None gracefully
            # so AllowAny endpoints (like login & register) continue to work.
            return None

        if not token.user.is_active:
            return None

        return (token.user, token)
