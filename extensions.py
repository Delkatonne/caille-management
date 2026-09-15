"""
extensions.py
--------------
Instance SQLAlchemy partagée par le module "caille".

INTEGRATION DANS HITNA :
Si l'application HITNA a déjà un objet `db = SQLAlchemy()` (généralement
dans app.py ou models.py), NE PAS créer un second objet db : supprimez ce
fichier et remplacez, dans models.py et routes/caille.py, la ligne
    from extensions import db
par
    from app import db   # ou l'import correspondant à votre projet
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
