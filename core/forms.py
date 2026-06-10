from django import forms
from django.forms import inlineformset_factory
from .models import Servico, Cliente, Empregado, TipoServico, GastoExtra, AnexoServico, Configuracao


class TipoServicoForm(forms.ModelForm):
    class Meta:
        model = TipoServico
        fields = [
            "nome",
            "descricao",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "descricao": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class EmpregadoForm(forms.ModelForm):
    class Meta:
        model = Empregado
        fields = [
            "nome",
            "cpf",
            "cargo",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "cpf": forms.TextInput(attrs={"class": "form-control", "data-mask": "cpf"}),
            "cargo": forms.TextInput(attrs={"class": "form-control"}),
        }


class ServicoForm(forms.ModelForm):
    class Meta:
        model = Servico
        fields = [
            "tecnico",
            "cliente",
            "tipo_servico",
            "descricao",
            "pecas_utilizadas",
            "data_inicio",
            "data_conclusao",
            "km_rodado",
            "valor_km",
            "hora_trabalhada",
            "valor_hora",
            "status",
        ]
        widgets = {
            "tecnico": forms.Select(attrs={"class": "form-control"}),
            "cliente": forms.Select(attrs={"class": "form-control"}),
            "tipo_servico": forms.Select(attrs={"class": "form-control"}),
            "descricao": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "pecas_utilizadas": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "data_inicio": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "data_conclusao": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "km_rodado": forms.NumberInput(attrs={"class": "form-control"}),
            "valor_km": forms.NumberInput(attrs={"class": "form-control"}),
            "hora_trabalhada": forms.NumberInput(attrs={"class": "form-control"}),
            "valor_hora": forms.NumberInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }


class GastoExtraForm(forms.ModelForm):
    class Meta:
        model = GastoExtra
        fields = ["descricao", "valor"]
        widgets = {
            "descricao": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Peça, ferramenta..."}),
            "valor": forms.NumberInput(attrs={"class": "form-control gasto-valor", "placeholder": "0.00"}),
        }


GastoExtraFormSet = inlineformset_factory(
    Servico, GastoExtra, form=GastoExtraForm,
    extra=1, can_delete=True,
)


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "nome",
            "email",
            "telefone",
            "documento",
            "endereco",
            "latitude",
            "longitude",
            "ativo",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "telefone": forms.TextInput(attrs={"class": "form-control", "data-mask": "telefone"}),
            "documento": forms.TextInput(attrs={"class": "form-control", "data-mask": "documento"}),
            "endereco": forms.TextInput(attrs={"class": "form-control"}),
            "latitude": forms.NumberInput(attrs={"class": "form-control"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class AnexoServicoForm(forms.ModelForm):
    class Meta:
        model = AnexoServico
        fields = ["arquivo", "descricao"]
        widgets = {
            "arquivo": forms.ClearableFileInput(attrs={"class": "form-control form-control-sm"}),
            "descricao": forms.Textarea(attrs={
                "class": "form-control form-control-sm",
                "rows": 2,
                "placeholder": "Descrição da imagem/vídeo...",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["arquivo"].required = False

    def clean_arquivo(self):
        arquivo = self.cleaned_data.get("arquivo")
        if not arquivo and self.instance and self.instance.pk:
            return self.instance.arquivo
        return arquivo


AnexoServicoFormSet = inlineformset_factory(
    Servico, AnexoServico, form=AnexoServicoForm,
    extra=1, can_delete=True,
)


class ConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = Configuracao
        fields = [
            "nome_empresa",
            "cnpj",
            "endereco",
            "telefone",
            "email",
            "logo",
            "texto_cabecalho",
            "texto_rodape",
            "chave_pix",
            "tipo_chave_pix",
        ]
        widgets = {
            "nome_empresa": forms.TextInput(attrs={"class": "form-control"}),
            "cnpj": forms.TextInput(attrs={"class": "form-control", "data-mask": "documento"}),
            "endereco": forms.TextInput(attrs={"class": "form-control"}),
            "telefone": forms.TextInput(attrs={"class": "form-control", "data-mask": "telefone"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "logo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "texto_cabecalho": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "texto_rodape": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "chave_pix": forms.TextInput(attrs={"class": "form-control"}),
            "tipo_chave_pix": forms.Select(attrs={"class": "form-control"}),
        }
