"""
用户认证相关 API 视图
提供：注册、获取/更新用户信息、修改密码
JWT Token 的获取(登录)和刷新由 SimpleJWT 内置视图处理
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """
    用户注册
    请求体: { "username": "", "password": "", "password2": "", "email": "" }
    """
    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')
    password2 = request.data.get('password2', '')
    email = request.data.get('email', '').strip()

    # 参数校验
    if not username or not password:
        return Response(
            {'detail': '用户名和密码不能为空'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if password != password2:
        return Response(
            {'detail': '两次输入的密码不一致'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if User.objects.filter(username=username).exists():
        return Response(
            {'detail': '该用户名已被注册'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if email and User.objects.filter(email=email).exists():
        return Response(
            {'detail': '该邮箱已被注册'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 密码强度校验
    try:
        validate_password(password)
    except ValidationError as e:
        return Response(
            {'detail': e.messages[0]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # 创建用户
    user = User.objects.create_user(
        username=username,
        password=password,
        email=email,
    )

    return Response(
        {
            'detail': '注册成功',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
            },
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    获取 / 更新当前用户信息
    GET  → 返回用户基本信息
    PUT  → 更新 email、first_name、last_name
    """
    user = request.user

    if request.method == 'GET':
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'date_joined': user.date_joined,
            'is_staff': user.is_staff,
        })

    # PUT 更新
    email = request.data.get('email', user.email).strip()
    first_name = request.data.get('first_name', user.first_name).strip()
    last_name = request.data.get('last_name', user.last_name).strip()

    # 检查邮箱是否被其他人占用
    if email and User.objects.filter(email=email).exclude(pk=user.pk).exists():
        return Response(
            {'detail': '该邮箱已被其他用户使用'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.email = email
    user.first_name = first_name
    user.last_name = last_name
    user.save()

    return Response({
        'detail': '更新成功',
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        },
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    修改密码
    请求体: { "old_password": "", "new_password": "", "new_password2": "" }
    """
    user = request.user
    old_password = request.data.get('old_password', '')
    new_password = request.data.get('new_password', '')
    new_password2 = request.data.get('new_password2', '')

    if not user.check_password(old_password):
        return Response(
            {'detail': '原密码错误'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if new_password != new_password2:
        return Response(
            {'detail': '两次输入的新密码不一致'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        validate_password(new_password, user)
    except ValidationError as e:
        return Response(
            {'detail': e.messages[0]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user.set_password(new_password)
    user.save()

    return Response({'detail': '密码修改成功，请重新登录'})
