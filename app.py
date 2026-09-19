"""
app.py — Application Flask du module "caille" pour HITNA.

Lancement rapide (SQLite local, aucune config nécessaire) :
    pip install -r requirements.txt
    python app.py
Puis ouvrez http://127.0.0.1:5000/caille/

Identifiant par défaut au premier lancement : admin / changeme123
(à changer via les variables d'environnement ADMIN_USERNAME / ADMIN_PASSWORD
avant le tout premier démarrage, ou en modifiant le mot de passe ensuite).
"""
import os
from flask import Flask, redirect, url_for

from extensions import db, login_manager
from routes.caille import caille_bp
from routes.auth import auth_bp


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Par défaut : SQLite local pour tester rapidement.
    # En production (Vercel), définissez DATABASE_URL (ex: votre base Neon).
    default_db = "sqlite:///" + os.path.join(os.path.dirname(__file__), "caille_test.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", default_db)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(caille_bp)
    app.register_blueprint(auth_bp)

    @app.route("/")
    def index():
        return redirect(url_for("caille.dashboard"))

    with app.app_context():
        db.create_all()
        _seed_especes_si_vide()
        _seed_types_provende_si_vide()
        _seed_admin_si_vide()

    return app


@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))


def _seed_especes_si_vide():
    """Crée l'espèce « Caille » par défaut si aucune n'existe encore.
    D'autres espèces (Poule, Lapin, ...) peuvent être ajoutées depuis
    l'interface (page Espèces / Types d'élevage)."""
    from models import Espece
    if Espece.query.count() == 0:
        db.session.add(Espece(nom="Caille", description="Élevage de cailles (ponte / chair)"))
        db.session.commit()


def _seed_types_provende_si_vide():
    """Pré-remplit les 3 types de provende classiques si la table est vide."""
    from models import TypeProvende
    if TypeProvende.query.count() == 0:
        defaults = [
            TypeProvende(nom="Démarrage", description="0 à 3 semaines, riche en protéines (~28%)", seuil_alerte_kg=15),
            TypeProvende(nom="Croissance", description="3 à 6 semaines (~22% protéines)", seuil_alerte_kg=15),
            TypeProvende(nom="Ponte", description="Dès l'entrée en ponte, avec calcium (~20% protéines)", seuil_alerte_kg=20),
        ]
        db.session.add_all(defaults)
        db.session.commit()


def _seed_admin_si_vide():
    """Crée un premier compte administrateur si aucun utilisateur n'existe.

    Identifiants configurables via les variables d'environnement
    ADMIN_USERNAME / ADMIN_PASSWORD. À défaut : admin / changeme123
    (à changer immédiatement après le premier déploiement)."""
    from models import User
    if User.query.count() == 0:
        username = os.environ.get("ADMIN_USERNAME", "admin")
        password = os.environ.get("ADMIN_PASSWORD", "changeme123")
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)