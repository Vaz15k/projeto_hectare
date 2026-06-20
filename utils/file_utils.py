from django.core.exceptions import ValidationError


def validar_tamanho_arquivo(value):
    """Valida que o arquivo não exceda 10 MB."""
    limite = 10 * 1024 * 1024  # 10 MB
    if value.size > limite:
        raise ValidationError(
            f"O arquivo não pode ser maior que 10 MB. "
            f"Tamanho atual: {value.size / (1024 * 1024):.2f} MB"
        )
