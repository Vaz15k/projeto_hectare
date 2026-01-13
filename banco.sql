USUARIO (id_usuario, nome_usuario, email, senha, tipo_usuario, data_criacao, data_alteracao, data_fim, is_active)

CLIENTE (id_cliente, nome_cliente, documento, telefone, email, endereco, latitude, longitude)

TIPO_SERVICO (id_tipo_servico, nome_servico)

SERVICO (id_servico, cliente_id, data_competencia, data_servico, km_rodado, preco_km, preco_servico, preco_total, pecas_utilizadas, descricao_servico, tipo_servico_id, status_servico)
- cliente_id references CLIENTE(id_cliente)
- tipo_servico_id references TIPO_SERVICO(id_tipo_servico)

NOTA_FISCAL (id_nota_fiscal, servico_id, data_emissao, valor_total, descricao_nota)
- servico_id references SERVICO(id_servico)`