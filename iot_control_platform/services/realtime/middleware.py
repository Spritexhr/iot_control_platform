"""
WebSocket JWT 鉴权中间件。

由于浏览器 WebSocket 不支持自定义 Authorization header，
握手时只能通过 query string 带 token：ws://host/ws/...?token=<jwt>

约定的 close code：
    4001 = 未认证 / token 无效
    4003 = 权限不足（保留给后续按资源 ACL 用）
"""
from __future__ import annotations

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

log = logging.getLogger(__name__)


@database_sync_to_async
def _authenticate(token: str):
    """同步 JWT 校验。失败统一返回 AnonymousUser。"""
    if not token:
        return AnonymousUser()
    try:
        from django.contrib.auth import get_user_model
        from rest_framework_simplejwt.tokens import AccessToken

        payload = AccessToken(token)
        user_id = payload.get("user_id")
        if user_id is None:
            return AnonymousUser()
        User = get_user_model()
        return User.objects.get(pk=user_id)
    except Exception as exc:
        log.debug("[ws-auth] token 校验失败: %s", exc)
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    """从 query string 解析 token 注入 scope['user']。"""

    async def __call__(self, scope, receive, send):
        qs = (scope.get("query_string") or b"").decode("utf-8", errors="ignore")
        token = (parse_qs(qs).get("token") or [""])[0]
        scope["user"] = await _authenticate(token)
        return await super().__call__(scope, receive, send)
