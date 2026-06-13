from django import forms
from django.forms import inlineformset_factory
from servicos.models import Servico, TipoServico, GastoExtra, AnexoServico, PecaUtilizada
from clientes.models import Maquina


class TipoServicoForm(forms.ModelForm):
    class Meta:
        model = TipoServico
        fields = ["nome", "descricao"]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "descricao": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class ServicoForm(forms.ModelForm):
    maquinas = forms.ModelMultipleChoiceField(
        queryset=Maquina.objects.filter(ativo=True),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input maquina-checkbox"}),
        label="Máquinas Atendidas",
        help_text="Selecione uma ou mais máquinas do cliente",
    )

    class Meta:
        model = Servico
        fields = [
            "tecnico", "cliente", "tipo_servico", "maquinas",
            "descricao", "problema_relatado", "diagnostico", "solucao",
            "data_inicio", "data_conclusao",
            "km_rodado", "valor_km", "hora_trabalhada", "valor_hora",
            "status",
        ]
        widgets = {
            "tecnico": forms.Select(attrs={"class": "form-control"}),
            "cliente": forms.Select(attrs={"class": "form-control"}),
            "tipo_servico": forms.Select(attrs={"class": "form-control"}),
            "descricao": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "problema_relatado": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "diagnostico": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "solucao": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
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
            "descricao": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "Ex: Peça, ferramenta..."
            }),
            "valor": forms.NumberInput(attrs={
                "class": "form-control gasto-valor", "placeholder": "0.00"
            }),
        }


GastoExtraFormSet = inlineformset_factory(
    Servico, GastoExtra, form=GastoExtraForm,
    extra=0, can_delete=True,
)


class AnexoServicoForm(forms.ModelForm):
    class Meta:
        model = AnexoServico
        fields = ["arquivo", "descricao"]
        widgets = {
            "arquivo": forms.FileInput(attrs={"class": "form-control form-control-sm"}),
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
    extra=0, can_delete=True,
)


class PecaUtilizadaForm(forms.ModelForm):
    class Meta:
        model = PecaUtilizada
        fields = ["nome", "quantidade", "valor_unitario"]
        widgets = {
            "nome": forms.TextInput(attrs={
                "class": "form-control", "placeholder": "Ex: Rolamento 6205"
            }),
            "quantidade": forms.NumberInput(attrs={
                "class": "form-control peca-qtd", "placeholder": "1"
            }),
            "valor_unitario": forms.NumberInput(attrs={
                "class": "form-control peca-valor", "placeholder": "0.00"
            }),
        }


PecaUtilizadaFormSet = inlineformset_factory(
    Servico, PecaUtilizada, form=PecaUtilizadaForm,
    extra=0, can_delete=True,
)
