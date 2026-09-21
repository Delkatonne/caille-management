"""blueprints/dashboard — Tableau de bord, statistiques et rapports."""
from flask import Blueprint

bp = Blueprint("dashboard", __name__)

# Les modules ci-dessous enregistrent leurs routes sur `bp` en s'important.
from . import home, statistiques, rapports  # noqa: E402,F401
