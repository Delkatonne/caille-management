"""
blueprints/auth — Connexion / déconnexion / changement de mot de passe.

Les rôles (employé / gérant / propriétaire) sont définis dans permissions.py ;
la gestion des comptes est dans utilisateurs.py (réservée au propriétaire).
La protection des pages est appliquée globalement dans app.py (before_request).
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db, login_manager
from models import User

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if not user.actif:
                flash("Ce compte est désactivé. Contactez le propriétaire.", "danger")
                return render_template("auth/login.html")
            login_user(user)
            flash("Connexion réussie.", "success")
            # On n'accepte qu'une adresse interne (évite les redirections vers un site externe)
            next_page = request.args.get("next")
            if not (next_page and next_page.startswith("/") and not next_page.startswith("//")):
                next_page = None
            return redirect(next_page or url_for("dashboard.dashboard"))
        flash("Identifiant ou mot de passe incorrect.", "danger")
    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/compte/mot-de-passe", methods=["GET", "POST"])
@login_required
def changer_mot_de_passe():
    if request.method == "POST":
        ancien = request.form.get("ancien_mot_de_passe", "")
        nouvel_identifiant = request.form.get("nouvel_identifiant", "").strip()
        nouveau = request.form.get("nouveau_mot_de_passe", "")
        confirmation = request.form.get("confirmation", "")

        if not current_user.check_password(ancien):
            flash("Le mot de passe actuel est incorrect.", "danger")
            return render_template("auth/changer_mot_de_passe.html")

        changements = []

        if nouvel_identifiant and nouvel_identifiant != current_user.username:
            deja_pris = User.query.filter(
                User.username == nouvel_identifiant, User.id != current_user.id
            ).first()
            if deja_pris:
                flash("Cet identifiant est déjà utilisé.", "danger")
                return render_template("auth/changer_mot_de_passe.html")
            current_user.username = nouvel_identifiant
            changements.append("identifiant")

        if nouveau or confirmation:
            if len(nouveau) < 6:
                flash("Le nouveau mot de passe doit contenir au moins 6 caractères.", "danger")
                return render_template("auth/changer_mot_de_passe.html")
            if nouveau != confirmation:
                flash("La confirmation ne correspond pas au nouveau mot de passe.", "danger")
                return render_template("auth/changer_mot_de_passe.html")
            current_user.set_password(nouveau)
            changements.append("mot de passe")

        if not changements:
            flash("Aucune modification renseignée.", "warning")
            return render_template("auth/changer_mot_de_passe.html")

        db.session.commit()
        flash("Mise à jour réussie : " + " et ".join(changements) + ".", "success")
        return redirect(url_for("dashboard.dashboard"))

    return render_template("auth/changer_mot_de_passe.html")


@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    return user if user and user.actif else None


from . import utilisateurs  # noqa: E402,F401
