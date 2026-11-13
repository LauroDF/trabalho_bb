# Testes automatizados

## Conteúdo

- `test/__init__.py`: identifica `test` como pacote Python.
- `test/conftest.py`: fixtures do pytest, banco SQLite temporário e cliente Flask.
- `test/test_bank_repository.py`: testes de persistência SQLite.
- `test/test_bank_service.py`: testes das regras de negócio.
- `test/test_bank_router.py`: testes HTTP dos endpoints Flask.
- `test/test_redis.py`: testes do cache Redis usando um cliente falso em memória.

## Segurança dos dados

Os testes de repositório substituem `bank_repository.DB_PATH` por um banco temporário criado pelo pytest. O arquivo `data/clients.db` do projeto não é utilizado nem alterado. Os testes Redis também não precisam de um servidor Redis ativo.

Os testes do router substituem o módulo leitor RFID antes de importar o Flask, evitando inicialização de GPIO ou acesso ao hardware real.

## Execução

Na raiz `trabalho_bb/`:

```bash
uv sync --extra test
uv run pytest
```

Ou, com ambiente virtual e dependências instaladas:

```bash
python -m pytest -v
```
