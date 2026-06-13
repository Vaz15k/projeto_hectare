from django import forms
from django.contrib.auth import authenticate


class LoginForm(forms.Form):
    """
    Formulário de login com campo único "login"
    que aceita email OU username.
    """

    login = forms.CharField(
        label="Email ou Usuário",
        max_length=254,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Digite seu email ou nome de usuário",
            "autofocus": True,
        }),
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Digite sua senha",
        }),
    )

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        login = cleaned_data.get("login")
        password = cleaned_data.get("password")

        if login and password:
            self.user_cache = authenticate(
                self.request,
                username=login,
                password=password,
            )
            if self.user_cache is None:
                raise forms.ValidationError(
                    "Email/usuário ou senha inválidos."
                )

        return cleaned_data

    def get_user(self):
        return self.user_cache
