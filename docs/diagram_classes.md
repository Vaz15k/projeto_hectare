```mermaid

classDiagram
    direction TB

    class Cliente {
        +String nome
        +String email
        +String telefone
        +String documento
        +String endereco
        +Decimal latitude
        +Decimal longitude
        +Boolean ativo
    }

    class Empregado {
        +String nome
        +String cpf
        +String cargo
    }

    class TipoServico {
        +String nome
        +String descricao
    }

    class Servico {
        +String descricao
        +String pecas_utilizadas
        +DateTime data_criacao
        +DateTime data_inicio
        +DateTime data_conclusao
        +DateTime data_competencia
        +Decimal km_rodado
        +Decimal valor_km
        +Decimal hora_trabalhada
        +Decimal valor_hora
        +Decimal valor_total
        +String status
        +save()
    }

    class AnexoServico {
        +File arquivo
        +String descricao
        +DateTime data_upload
        +is_image() Boolean
        +is_video() Boolean
    }

    class NotaFiscal {
        +String numero_nota_fiscal
        +Decimal valor_total
        +String descricao_nota
        +DateTime data_emissao
    }

    class GastoExtra {
        +String descricao
        +Decimal valor
    }

    class Configuracao {
        +String nome_empresa
        +String cnpj
        +String endereco
        +String telefone
        +String email
        +Image logo
        +String texto_cabecalho
        +String texto_rodape
        +String chave_pix
        +String tipo_chave_pix
        +load() Configuracao
    }

    class QRCodePix {
        +gerar_payload() String
        +gerar_imagem() Image
    }

    Cliente "1" <-- "0..*" Servico : solicita
    Empregado "1" <-- "0..*" Servico : realiza (tecnico)
    TipoServico "1" <-- "0..*" Servico : categoriza
    Servico "1" *-- "0..*" AnexoServico : contém
    Servico "1" o-- "0..*" NotaFiscal : gera
    Servico "1" *-- "0..*" GastoExtra : possui
    Configuracao "1" --> "0..*" QRCodePix : gera