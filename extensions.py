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
from flask_login import LoginManager

db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "warning"