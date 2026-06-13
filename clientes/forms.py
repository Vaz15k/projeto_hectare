from django import forms
from django.forms import inlineformset_factory
from clientes.models import Cliente, Maquina


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "nome", "email", "telefone", "documento",
            "endereco", "latitude", "longitude", "ativo",
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


class MaquinaForm(forms.ModelForm):
    class Meta:
        model = Maquina
        fields = ["nome", "marca", "modelo", "numero_serie", "ano", "foto", "ativo"]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: Trator Massey Ferguson"}),
            "marca": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: John Deere"}),
            "modelo": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: MF 290"}),
            "numero_serie": forms.TextInput(attrs={"class": "form-control", "placeholder": "Número de série"}),
            "ano": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Ex: 2020"}),
            "foto": forms.FileInput(attrs={"class": "form-control form-control-sm"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        if self.data.get(self.add_prefix("foto-clear")):
            if self.instance and self.instance.pk and self.instance.foto:
                self.instance.foto.delete(save=False)
            return None
        if not foto and self.instance and self.instance.pk:
            return self.instance.foto
        return foto


MaquinaInlineFormSet = inlineformset_factory(
    Cliente, Maquina, form=MaquinaForm,
    extra=0, can_delete=True,
    fields=["nome", "marca", "modelo", "numero_serie", "ano", "foto", "ativo"],
    widgets={
        "nome": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Ex: Trator Massey Ferguson"}),
        "marca": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Ex: John Deere"}),
        "modelo": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Ex: MF 290"}),
        "numero_serie": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Nº de série"}),
        "ano": forms.NumberInput(attrs={"class": "form-control form-control-sm", "placeholder": "Ex: 2020"}),
        "foto": forms.FileInput(attrs={"class": "form-control form-control-sm"}),
        "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
    },
)
