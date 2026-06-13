"""
Backend de autenticação customizado que permite login com email OU username.

Como o sistema é fechado (acesso restrito a funcionários), não há
registro público — os usuários são criados pelo admin via Django Admin
ou pelo comando `manage.py createsuperuser`.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

UserModel = get_user_model()


class EmailOrUsernameBackend(ModelBackend):
    """
    Autentica o usuário usando email OU username (ambos com a mesma senha).

    O form de login terá um único campo "login" onde o usuário pode digitar
    tanto o email quanto o username.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)

        if username is None or password is None:
            return None

        try:
            user = UserModel.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
        except UserModel.DoesNotExist:
            # Executa o set_password padrão para evitar timing attack
            UserModel().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
