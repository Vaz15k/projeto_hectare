from django import forms
from .models import Servico, Cliente, Empregado, TipoServico


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
            "cpf": forms.TextInput(attrs={"class": "form-control"}),
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
            "valor_servico",
            "valor_total",
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
            "valor_servico": forms.NumberInput(attrs={"class": "form-control"}),
            "valor_total": forms.NumberInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }


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
            "telefone": forms.TextInput(attrs={"class": "form-control"}),
            "documento": forms.TextInput(attrs={"class": "form-control"}),
            "endereco": forms.TextInput(attrs={"class": "form-control"}),
            "latitude": forms.NumberInput(attrs={"class": "form-control"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control"}),
            "ativo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
