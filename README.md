Documentação do código — trabalho_bb

---

1. Camada de rotas

`routers/bank_router.py`

Define as rotas HTTP. Cada rota extrai os dados da requisição, chama a função correspondente do serviço e traduz as exceções em respostas JSON.

Formato das respostas

- Sucesso: `{"success": true, "message": "...", "data": ...}`
- Erro: `{"success": false, "message": "..."}`
- Qualquer exceção não prevista gera status 500 com a mensagem "Ocorreu um erro inesperado no sistema".

`home()` — `GET /`
Retorna `{"message": "API funcionando"}` com status 200. Serve como verificação de que a API está no ar.

`register_account()` — `POST /api/clients`
Cadastra uma conta.

- Corpo (JSON): `name`, `cpf`, `password`, `rfid`.

`login_account()` — `POST /api/auth`
Autentica um cliente.

- Corpo (JSON): `rfid`, `password`.

`update_account(id)` — `PATCH /api/clients/<id>`
Atualiza dados do cliente.

- Corpo (JSON): `name`, `cpf`, `password`, `rfid` (todos opcionais na rota).

`get_data_account(id)` — `GET /api/clients/<id>`
Consulta os dados de um cliente.

`withdraw_account(id)` — `PATCH /api/clients/<id>/withdraw`
Realiza um saque.

- Corpo (JSON): `balance` (valor a sacar).

`deposit_account(id)` — `PATCH /api/clients/<id>/deposit`
Realiza um depósito.

- Corpo (JSON): `balance` (valor a depositar).

`delete_account(id)` — `DELETE /api/clients/<id>`
Exclui uma conta.

`read_rfid_card()` — `GET /api/rfid`
Aguarda a aproximação de uma tag e devolve seu identificador.

---

2. Camada de serviço

`services/bank_service.py`

Concentra as regras de negócio: validação de entrada, hash de senha.

- Validações:
  1. Campos obrigatórios (nome, CPF, senha, RFID).
  2. Nome com 3 a 100 caracteres.
  3. Senha com 8 a 128 caracteres.
  4. CPF válido segundo `validate_docbr`.
  5. RFID com 8 a 15 caracteres.
  6. Valor de saque deve ser maior que 0 e no máximo 10.000
  7. Valor de depósito deve ser maior que 0 e no máximo 1.000.000.

---

3. Camada de repositório

`repositories/bank_repository.py`

Acesso ao banco SQLite. Cada função abre sua própria conexão e a fecha.

Restrições da tabela:
- `id` TEXT, chave primária;
- `name` TEXT, obrigatório;
- `cpf` TEXT, único, obrigatório, com exatamente 11 caracteres;
- `password` TEXT, obrigatório, com pelo menos 8 caracteres;
- `rfid` TEXT, único, obrigatório;
- `balance` REAL, padrão 0.0.

---

4. Cache

`cache/schemas.py`

`cache/redis.py`

O Redis funciona como cache de dados de clientes: grava cada registro como JSON na chave client:{id}, com expiração após 300 segundos.

Na consulta de conta, tenta ler o cache e, se não encontrar, busca no SQLite e o atualiza; criação, edição, depósito e saque também atualizam o cache, e a exclusão o invalida.

O SQLite continua sendo a fonte persistente dos dados; falhas do Redis são registradas e não impedem a operação com o banco, e, fora do Docker sem Redis disponível, o app usa um cache no-op.

---

5. Hardware

`hardware/tag_reader.py`

- Faz a comunicação com o leitor RFID da raspi, e no começo, era para funcionar com led RGB e o buzzer

- Tem timeout de 15 segundos

---

6. Exceções

`exceptions/exceptions.py`

Todas herdam de `Exception` e não têm comportamento próprio. A mensagem é definida no ponto onde são lançadas.