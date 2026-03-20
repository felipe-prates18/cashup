#!/usr/bin/env python3
"""Script standalone para remover todos os lançamentos do banco SQLite do CashUp.

Este utilitário foi pensado para execução direta no servidor e não depende do
backend da aplicação. Ele atua apenas no arquivo SQLite informado.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

CONFIRMATION_TEXT = "LIMPAR"


def infer_default_db_path() -> Path:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    env_path = os.getenv("CASHUP_DB")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return (repo_root / "backend" / "cashup.db").resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove todos os lançamentos da base SQLite do CashUp sem usar a aplicação.",
    )
    parser.add_argument(
        "--db",
        default=str(infer_default_db_path()),
        help="Caminho para o arquivo SQLite. Padrão: backend/cashup.db ou $CASHUP_DB.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Executa sem pedir confirmação interativa.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra o que seria alterado sem gravar mudanças.",
    )
    return parser.parse_args()


def fetch_scalar(cursor: sqlite3.Cursor, query: str) -> int:
    row = cursor.execute(query).fetchone()
    return int(row[0] if row and row[0] is not None else 0)


def confirm(force: bool, db_path: Path, transaction_count: int) -> None:
    if force:
        return

    print(f"Banco alvo: {db_path}")
    print(f"Lançamentos encontrados: {transaction_count}")
    typed = input(f"Digite {CONFIRMATION_TEXT} para continuar: ").strip().upper()
    if typed != CONFIRMATION_TEXT:
        print("Operação cancelada.")
        raise SystemExit(1)


def ensure_db_exists(db_path: Path) -> None:
    if not db_path.exists():
        print(f"Arquivo de banco não encontrado: {db_path}", file=sys.stderr)
        raise SystemExit(1)


def run_cleanup(db_path: Path, dry_run: bool) -> dict[str, int]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        metrics = {
            "transactions": fetch_scalar(cursor, "SELECT COUNT(*) FROM transactions"),
            "linked_titles": fetch_scalar(cursor, "SELECT COUNT(*) FROM titles WHERE transaction_id IS NOT NULL"),
            "linked_reconciliation": fetch_scalar(
                cursor,
                "SELECT COUNT(*) FROM reconciliation_items WHERE matched_transaction_id IS NOT NULL",
            ),
        }

        if dry_run:
            return metrics

        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("UPDATE titles SET transaction_id = NULL WHERE transaction_id IS NOT NULL")
        cursor.execute(
            "UPDATE reconciliation_items "
            "SET matched_transaction_id = NULL, status = 'Pendente' "
            "WHERE matched_transaction_id IS NOT NULL"
        )
        cursor.execute("DELETE FROM transactions")
        cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'transactions'")
        connection.commit()
        return metrics
    except sqlite3.Error as exc:
        connection.rollback()
        print(f"Falha ao limpar lançamentos: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    finally:
        connection.close()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db).expanduser().resolve()
    ensure_db_exists(db_path)

    preview = run_cleanup(db_path, dry_run=True)
    confirm(args.force, db_path, preview["transactions"])

    if args.dry_run:
        print("Pré-visualização concluída.")
    else:
        run_cleanup(db_path, dry_run=False)
        print("Limpeza concluída com sucesso.")

    print(f"- lançamentos: {preview['transactions']}")
    print(f"- títulos desvinculados: {preview['linked_titles']}")
    print(f"- itens de conciliação resetados: {preview['linked_reconciliation']}")


if __name__ == "__main__":
    main()
