"""Herramientas de línea de comandos.

    python -m nutripae.cli crear-admin USUARIO CONTRASENA [--nombre NOMBRE]
    python -m nutripae.cli borrar-fotos-antiguas --antes YYYY-MM-DD
"""
from __future__ import annotations

import argparse
import sys
from datetime import date

from nutripae import auth, config, db, retention


def _fecha(texto: str) -> date:
    try:
        return date.fromisoformat(texto)
    except ValueError:
        raise argparse.ArgumentTypeError("usa el formato AAAA-MM-DD") from None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="nutripae.cli")
    sub = ap.add_subparsers(dest="orden", required=True)
    p = sub.add_parser("crear-admin", help="Crea un usuario administrador")
    p.add_argument("usuario")
    p.add_argument("contrasena")
    p.add_argument("--nombre", default=None)
    b = sub.add_parser("borrar-fotos-antiguas",
                       help="Borra las fotos tomadas antes de una fecha (fin del año escolar)")
    b.add_argument("--antes", type=_fecha, required=True, help="Fecha límite AAAA-MM-DD (no incluida)")
    args = ap.parse_args(argv)

    settings = config.cargar()
    con = db.conectar(settings.db_path)
    try:
        if args.orden == "borrar-fotos-antiguas":
            n = retention.borrar_fotos_antes(con, settings, args.antes)
            print(f"Fotos eliminadas: {n}")
            return 0
        try:
            auth.crear_usuario(con, args.usuario, args.nombre or args.usuario,
                               args.contrasena, ["admin"], [])
        except ValueError as e:
            print(e, file=sys.stderr)
            return 1
        print("Usuario administrador creado")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
