"""Herramientas de línea de comandos: python -m nutripae.cli crear-admin ..."""
from __future__ import annotations

import argparse
import sys

from nutripae import auth, config, db


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="nutripae.cli")
    sub = ap.add_subparsers(dest="orden", required=True)
    p = sub.add_parser("crear-admin", help="Crea un usuario administrador")
    p.add_argument("usuario")
    p.add_argument("contrasena")
    p.add_argument("--nombre", default=None)
    args = ap.parse_args(argv)

    con = db.conectar(config.cargar().db_path)
    try:
        auth.crear_usuario(con, args.usuario, args.nombre or args.usuario,
                           args.contrasena, ["admin"], [])
    except ValueError as e:
        print(e, file=sys.stderr)
        return 1
    print("Usuario administrador creado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
