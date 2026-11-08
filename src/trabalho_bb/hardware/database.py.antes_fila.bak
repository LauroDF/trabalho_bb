import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "data" / "sala_seguranca.db"


@contextmanager
def conectar():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(DATABASE_PATH, timeout=10)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")

    try:
        yield conexao
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def inicializar_banco():
    with conectar() as conexao:
        conexao.executescript("""
            CREATE TABLE IF NOT EXISTS colaboradores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                matricula TEXT NOT NULL UNIQUE,
                cargo TEXT NOT NULL,
                tag_uid TEXT NOT NULL UNIQUE,
                autorizado INTEGER NOT NULL DEFAULT 0
                    CHECK (autorizado IN (0, 1)),
                ativo INTEGER NOT NULL DEFAULT 1
                    CHECK (ativo IN (0, 1))
            );

            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL,
                ativo INTEGER NOT NULL DEFAULT 1
                    CHECK (ativo IN (0, 1))
            );

            CREATE TABLE IF NOT EXISTS eventos (
                event_id TEXT PRIMARY KEY,
                tag_uid TEXT NOT NULL,
                colaborador_id INTEGER,
                tipo TEXT NOT NULL CHECK (
                    tipo IN (
                        'ENTRADA',
                        'SAIDA',
                        'ACESSO_NEGADO',
                        'TENTATIVA_INVASAO'
                    )
                ),
                resultado TEXT NOT NULL CHECK (
                    resultado IN ('AUTORIZADO', 'NEGADO')
                ),
                ocorrido_em TEXT NOT NULL,
                origem TEXT NOT NULL DEFAULT 'raspberry_pi',
                sincronizado INTEGER NOT NULL DEFAULT 0
                    CHECK (sincronizado IN (0, 1)),
                FOREIGN KEY (colaborador_id)
                    REFERENCES colaboradores(id)
                    ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS idx_eventos_data
                ON eventos(ocorrido_em);

            CREATE INDEX IF NOT EXISTS idx_eventos_tag
                ON eventos(tag_uid);

            CREATE INDEX IF NOT EXISTS idx_eventos_sincronizacao
                ON eventos(sincronizado);
        """)

        colaboradores = [
            (
                "Funcionario A", "COLAB001", "Colaborador",
                "962185903074", 1, 1,
            ),
            (
                "Funcionario B", "COLAB002", "Colaborador",
                "701044494601", 1, 1,
            ),
            (
                "Funcionario C", "COLAB003", "Colaborador",
                "632092037175", 0, 1,
            ),
            (
                "Funcionario D", "COLAB004", "Colaborador",
                "427066982110", 0, 1,
            ),
        ]

        conexao.executemany("""
            INSERT OR IGNORE INTO colaboradores
                (nome, matricula, cargo, tag_uid, autorizado, ativo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, colaboradores)


def buscar_colaborador_por_tag(tag_uid):
    with conectar() as conexao:
        colaborador = conexao.execute("""
            SELECT id, nome, matricula, cargo, tag_uid,
                   autorizado, ativo
            FROM colaboradores
            WHERE tag_uid = ?
        """, (str(tag_uid),)).fetchone()

        return dict(colaborador) if colaborador else None


def registrar_evento(tag_uid, colaborador_id, tipo, resultado):
    ocorrido_em = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    with conectar() as conexao:
        conexao.execute("""
            INSERT INTO eventos (
                event_id, tag_uid, colaborador_id,
                tipo, resultado, ocorrido_em
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4()),
            str(tag_uid),
            colaborador_id,
            tipo,
            resultado,
            ocorrido_em,
        ))

    print(f"Evento registrado no SQLite: {tipo} - {resultado}")


if __name__ == "__main__":
    inicializar_banco()
    print(f"Banco inicializado em: {DATABASE_PATH}")
