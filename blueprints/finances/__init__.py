"""blueprints/finances — Finances et commercial : clients, ventes, fournisseurs, dépenses, rentabilité."""
from flask import Blueprint

bp = Blueprint("finances", __name__)

# Les modules ci-dessous enregistrent leurs routes sur `bp` en s'important.
from . import clients, ventes, fournisseurs, depenses, rentabilite  # noqa: E402,F401
