"""
app.py — Application Flask « HITNA Ferme » (gestion d'une ferme).

Lancement rapide (SQLite local, aucune config nécessaire) :
    pip install -r requirements.txt
    python app.py
Puis ouvrez http://127.0.0.1:5000/

Identifiant par défaut au premier lancement : admin / changeme123
(à changer via les variables d'environnement ADMIN_USERNAME / ADMIN_PASSWORD
avant le tout premier démarrage, ou en modifiant le mot de passe ensuite).

Architecture : voir README.md (un blueprint par bloc fonctionnel dans blueprints/).
"""
import os

from flask import Flask, abort, redirect, render_template, request
from flask_login import current_user

import permissions
import schema_updates
from extensions import db, login_manager
from blueprints import register_blueprints
from seeds import seed_all


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
    register_blueprints(app)

    permissions.verifier_regles(app)

    @app.before_request
    def controler_acces():
        """Connexion obligatoire (sauf pages publiques), puis contrôle du rôle (permissions.py)."""
        endpoint = request.endpoint
        if endpoint is None or endpoint == "static" or endpoint in permissions.ENDPOINTS_PUBLICS:
            return None
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if not permissions.autorise(current_user, endpoint, request.method):
            abort(403)

    @app.context_processor
    def outils_permissions():
        """Fonctions utilisables dans les templates pour masquer ce que le rôle ne permet pas."""
        def peut(role_minimum):
            return current_user.is_authenticated and permissions.niveau(current_user.role) >= permissions.niveau(role_minimum)

        def peut_acceder(endpoint, methode="GET"):
            return current_user.is_authenticated and permissions.autorise(current_user, endpoint, methode)

        return {"peut": peut, "peut_acceder": peut_acceder, "libelles_roles": permissions.LIBELLES}

    @app.errorhandler(403)
    def acces_refuse(_erreur):
        return render_template("errors/403.html"), 403

    @app.route("/caille/", defaults={"chemin": ""})
    @app.route("/caille/<path:chemin>")
    def ancienne_url(chemin):
        """Anciennes adresses (/caille/...) : redirigées vers les nouvelles (sans préfixe)."""
        cible = "/" + chemin.lstrip("/")
        if request.query_string:
            cible += "?" + request.query_string.decode()
        return redirect(cible, code=301)

    with app.app_context():
        db.create_all()
        schema_updates.appliquer()
        seed_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
