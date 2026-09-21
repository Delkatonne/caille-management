"""blueprints/production — Production : lots, espèces, ponte, mortalité, naissances, croissance, santé, archive."""
from flask import Blueprint

bp = Blueprint("production", __name__)

# Les modules ci-dessous enregistrent leurs routes sur `bp` en s'important.
from . import lots, especes, sante, croissance, ponte, mortalite, naissances  # noqa: E402,F401
