"""
app.py — Application Flask autonome pour TESTER le module "caille" en local.

Ceci n'est PAS destiné à remplacer votre application HITNA principale.
C'est un point d'entrée minimal qui vous permet de lancer et visiter le
module tout seul avant de l'intégrer. Voir README.md pour l'intégration
réelle dans votre projet HITNA existant.

Lancement rapide (SQLite local, aucune config nécessaire) :
    pip install -r requirements.txt
    python app.py
Puis ouvrez http://127.0.0.1:5000/caille/
"""
import os
from flask import Flask, redirect, url_for

from extensions import db
from routes.caille import caille_bp

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Par défaut : SQLite local pour tester rapidement.
    # Pour tester avec votre vraie base PostgreSQL, définissez la variable
    # d'environnement DATABASE_URL avant de lancer l'app.
    default_db = "sqlite:///" + os.path.join(os.path.dirname(__file__), "caille_test.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", default_db)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    app.register_blueprint(caille_bp)

    @app.route("/")
    def index():
        return redirect(url_for("caille.dashboard"))

    with app.app_context():
        db.create_all()
        _seed_types_provende_si_vide()

    return app


def _seed_types_provende_si_vide():
    """Pré-remplit les 3 types de provende classiques si la table est vide,
    pour que le tableau de bord ne soit pas vide au premier lancement."""
    from models import TypeProvende
    if TypeProvende.query.count() == 0:
        defaults = [
            TypeProvende(nom="Démarrage", description="0 à 3 semaines, riche en protéines (~28%)", seuil_alerte_kg=15),
            TypeProvende(nom="Croissance", description="3 à 6 semaines (~22% protéines)", seuil_alerte_kg=15),
            TypeProvende(nom="Ponte", description="Dès l'entrée en ponte, avec calcium (~20% protéines)", seuil_alerte_kg=20),
        ]
        db.session.add_all(defaults)
        db.session.commit()


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
