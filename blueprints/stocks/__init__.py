"""blueprints/stocks — Stocks et intrants : provende (types, achats, consommation)."""
from flask import Blueprint

bp = Blueprint("stocks", __name__)

# Les modules ci-dessous enregistrent leurs routes sur `bp` en s'important.
from . import provende  # noqa: E402,F401
