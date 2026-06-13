from django import forms
from core.models import Configuracao


class ConfiguracaoForm(forms.ModelForm):
    class Meta:
        model = Configuracao
        fields = [
            "nome_empresa", "cnpj", "endereco", "telefone", "email",
            "logo", "texto_cabecalho", "texto_rodape",
            "chave_pix", "tipo_chave_pix",
        ]
        widgets = {
            "nome_empresa": forms.TextInput(attrs={"class": "form-control"}),
            "cnpj": forms.TextInput(attrs={"class": "form-control", "data-mask": "documento"}),
            "endereco": forms.TextInput(attrs={"class": "form-control"}),
            "telefone": forms.TextInput(attrs={"class": "form-control", "data-mask": "telefone"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "logo": forms.FileInput(attrs={"class": "form-control"}),
            "texto_cabecalho": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "texto_rodape": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "chave_pix": forms.TextInput(attrs={"class": "form-control"}),
            "tipo_chave_pix": forms.Select(attrs={"class": "form-control"}),
        }

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if self.data.get(self.add_prefix("logo-clear")):
            if self.instance and self.instance.pk and self.instance.logo:
                self.instance.logo.delete(save=False)
            return None
        if not logo and self.instance and self.instance.pk:
            return self.instance.logo
        return logo
