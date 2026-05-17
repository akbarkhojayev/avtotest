from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.exceptions import AuthenticationFailed
from .models import UserSession


class SingleDeviceJWTAuthentication(JWTAuthentication):
    """
    Bitta qurilma cheklovi bilan JWT autentifikatsiya.
    Header: Authorization: Bearer <token>  yoki  ?token=<access> query param.
    """

    def authenticate(self, request):
        # 1. ?token= query param yoki Authorization header dan raw token olish
        query_token = request.query_params.get('token')
        if query_token:
            raw_token = query_token.encode()
        else:
            header = self.get_header(request)
            if header is None:
                return None
            raw_token = self.get_raw_token(header)
            if raw_token is None:
                return None

        # 2. Tokenni tekshirish
        try:
            validated_token = self.get_validated_token(raw_token)
        except (InvalidToken, TokenError):
            return None

        # 3. Foydalanuvchini olish
        user = self.get_user(validated_token)

        # 4. JTI sessiya tekshiruvi
        try:
            token_jti = str(validated_token.get('jti', ''))
        except Exception:
            raise AuthenticationFailed("Token noto'g'ri.")

        try:
            session = UserSession.objects.get(user=user)
            if session.token_jti and session.token_jti != token_jti:
                raise AuthenticationFailed(
                    "Siz boshqa qurilmadan tizimga kirgansiz. "
                    "Iltimos, qayta login qiling."
                )
        except UserSession.DoesNotExist:
            raise AuthenticationFailed("Sessiya topilmadi. Qayta login qiling.")

        return user, validated_token
