from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.exceptions import AuthenticationFailed
from .models import UserSession


class SingleDeviceJWTAuthentication(JWTAuthentication):
    """
    Bitta qurilma cheklovi bilan JWT autentifikatsiya.
    Har bir foydalanuvchi faqat bitta qurilmadan kirishi mumkin.
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, validated_token = result

        # Token JTI ni tekshirish
        try:
            token_jti = str(validated_token.get('jti', ''))
        except Exception:
            raise AuthenticationFailed("Token noto'g'ri.")

        # Foydalanuvchi sessiyasini tekshirish
        try:
            session = UserSession.objects.get(user=user)
            if session.token_jti and session.token_jti != token_jti:
                raise AuthenticationFailed(
                    "Siz boshqa qurilmadan tizimga kirgansiz. "
                    "Iltimos, qayta login qiling."
                )
        except UserSession.DoesNotExist:
            # Sessiya yo'q - bu holat bo'lmasligi kerak, lekin xavfsizlik uchun
            raise AuthenticationFailed("Sessiya topilmadi. Qayta login qiling.")

        return user, validated_token
