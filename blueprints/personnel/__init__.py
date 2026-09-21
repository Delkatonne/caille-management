"""blueprints/personnel — Personnel : employés et cahier de charges (tâches)."""
from flask import Blueprint

bp = Blueprint("personnel", __name__)

# Les modules ci-dessous enregistrent leurs routes sur `bp` en s'important.
from . import employes, taches  # noqa: E402,F401
