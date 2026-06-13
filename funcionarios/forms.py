from django import forms
from funcionarios.models import Empregado


class EmpregadoForm(forms.ModelForm):
    class Meta:
        model = Empregado
        fields = ["nome", "cpf", "cargo"]
        widgets = {
            "nome": forms.TextInput(attrs={"class": "form-control"}),
            "cpf": forms.TextInput(attrs={"class": "form-control", "data-mask": "cpf"}),
            "cargo": forms.TextInput(attrs={"class": "form-control"}),
        }
