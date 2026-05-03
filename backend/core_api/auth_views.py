"""
Panel JWT kimlik dogrulama gorunumleri — httpOnly cerez tabanli (SEC-002).

  - POST /api/auth/token/         → access + refresh cerezleri set; govde: kullanici profili
  - POST /api/auth/token/refresh/ → cerezdeki refresh ile yeni access yazar
  - POST /api/auth/logout/        → refresh blacklist + cerezleri temizle
"""
from __future__ import annotations

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken


class LoginRequestSerializer(serializers.Serializer):
    username = serializers.CharField(help_text="Panel kullanici adi")
    password = serializers.CharField(write_only=True, help_text="Panel sifresi")


class LoginResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    rol = serializers.CharField()
    eczane = serializers.IntegerField(allow_null=True)


class DetailErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()


def _cookie_kwargs(*, max_age_seconds: int) -> dict:
    return {
        "max_age": max_age_seconds,
        "httponly": True,
        "secure": getattr(settings, "JWT_COOKIE_SECURE", not settings.DEBUG),
        "samesite": getattr(settings, "JWT_COOKIE_SAMESITE", "Strict"),
        "path": "/",
        "domain": getattr(settings, "JWT_COOKIE_DOMAIN", None),
    }


def _set_access_cookie(response, token):
    lifetime = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]
    response.set_cookie(
        getattr(settings, "JWT_AUTH_COOKIE", "eisa_access"),
        token,
        **_cookie_kwargs(max_age_seconds=int(lifetime.total_seconds())),
    )


def _set_refresh_cookie(response, token):
    lifetime = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
    response.set_cookie(
        getattr(settings, "JWT_REFRESH_COOKIE", "eisa_refresh"),
        token,
        **_cookie_kwargs(max_age_seconds=int(lifetime.total_seconds())),
    )


def _delete_jwt_cookies(response):
    domain = getattr(settings, "JWT_COOKIE_DOMAIN", None)
    response.delete_cookie(getattr(settings, "JWT_AUTH_COOKIE", "eisa_access"), path="/", domain=domain)
    response.delete_cookie(getattr(settings, "JWT_REFRESH_COOKIE", "eisa_refresh"), path="/", domain=domain)


class CookieTokenObtainPairView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_scope = "login"

    @extend_schema(
        tags=["auth"], auth=[],
        request=LoginRequestSerializer,
        responses={200: LoginResponseSerializer,
                   401: OpenApiResponse(response=DetailErrorSerializer)},
        summary="Panel login",
    )
    def post(self, request):
        serializer = TokenObtainPairSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0])
        validated = serializer.validated_data
        user = serializer.user
        body = {
            "id": user.pk,
            "username": user.username,
            "rol": getattr(user, "rol", ""),
            "eczane": getattr(user, "eczane_id", None),
        }
        response = Response(body, status=status.HTTP_200_OK)
        _set_access_cookie(response, validated["access"])
        _set_refresh_cookie(response, validated["refresh"])
        return response


class CookieTokenRefreshView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_scope = "login"

    @extend_schema(tags=["auth"], auth=[], request=None,
                   responses={204: OpenApiResponse(),
                              401: OpenApiResponse(response=DetailErrorSerializer)},
                   summary="Token refresh")
    def post(self, request):
        cookie_name = getattr(settings, "JWT_REFRESH_COOKIE", "eisa_refresh")
        refresh_token = request.COOKIES.get(cookie_name)
        if not refresh_token:
            return Response({"detail": "Refresh cerezi bulunamadi."},
                            status=status.HTTP_401_UNAUTHORIZED)
        serializer = TokenRefreshSerializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0])
        validated = serializer.validated_data
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _set_access_cookie(response, validated["access"])
        if "refresh" in validated:
            _set_refresh_cookie(response, validated["refresh"])
        return response


class CookieLogoutView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    @extend_schema(tags=["auth"], auth=[], request=None,
                   responses={204: OpenApiResponse()},
                   summary="Logout")
    def post(self, request):
        cookie_name = getattr(settings, "JWT_REFRESH_COOKIE", "eisa_refresh")
        refresh_token = request.COOKIES.get(cookie_name)
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _delete_jwt_cookies(response)
        return response
