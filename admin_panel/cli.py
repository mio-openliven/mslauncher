from __future__ import annotations

import argparse
import getpass
import sqlite3
from pathlib import Path

from .db import connect, init_db
from .security import generate_password, hash_password
from .settings import get_database_path


def create_user(username: str, role: str, password: str, *, database_path: Path | None = None) -> None:
    init_db(database_path)
    with connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO users (username, password_hash, role, active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(username) DO UPDATE SET
                password_hash=excluded.password_hash,
                role=excluded.role,
                active=1
            """,
            (username, hash_password(password), role),
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MSLaunch panel admin CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Create panel database and default projects.")

    create_parser = subparsers.add_parser("create-user", help="Create or reset a panel user.")
    create_parser.add_argument("--username", required=True)
    create_parser.add_argument("--role", default="project_admin", choices=("owner", "project_admin", "viewer"))
    create_parser.add_argument("--password", default="")
    create_parser.add_argument("--print-password", action="store_true")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "init-db":
        init_db()
        print(f"Panel database ready: {get_database_path()}")
        return

    if args.command == "create-user":
        password = args.password
        if not password and args.print_password:
            password = generate_password()
        if not password:
            password = getpass.getpass("Password: ")
        create_user(args.username, args.role, password)
        print(f"User ready: {args.username} ({args.role})")
        if args.print_password:
            print(password)
        return

    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()

