"""
routes/auth.py — Connexion / déconnexion pour le module caille.

Un seul rôle pour l'instant (pas d'admin/employé séparés). Si HITNA a déjà
son propre système d'authentification, ce blueprint peut être retiré et
remplacé par le login existant (voir README.md).
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models import User

auth_bp = Blueprint(
    "auth", __name__,
    template_folder="../templates/caille",
)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Connexion réussie.", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("caille.dashboard"))
        flash("Identifiant ou mot de passe incorrect.", "danger")
    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/compte/mot-de-passe", methods=["GET", "POST"])
@login_required
def changer_mot_de_passe():
    if request.method == "POST":
        ancien = request.form.get("ancien_mot_de_passe", "")
        nouvel_identifiant = request.form.get("nouvel_identifiant", "").strip()
        nouveau = request.form.get("nouveau_mot_de_passe", "")
        confirmation = request.form.get("confirmation", "")

        if not current_user.check_password(ancien):
            flash("Le mot de passe actuel est incorrect.", "danger")
            return render_template("changer_mot_de_passe.html")

        changements = []

        if nouvel_identifiant and nouvel_identifiant != current_user.username:
            deja_pris = User.query.filter(
                User.username == nouvel_identifiant, User.id != current_user.id
            ).first()
            if deja_pris:
                flash("Cet identifiant est déjà utilisé.", "danger")
                return render_template("changer_mot_de_passe.html")
            current_user.username = nouvel_identifiant
            changements.append("identifiant")

        if nouveau or confirmation:
            if len(nouveau) < 6:
                flash("Le nouveau mot de passe doit contenir au moins 6 caractères.", "danger")
                return render_template("changer_mot_de_passe.html")
            if nouveau != confirmation:
                flash("La confirmation ne correspond pas au nouveau mot de passe.", "danger")
                return render_template("changer_mot_de_passe.html")
            current_user.set_password(nouveau)
            changements.append("mot de passe")

        if not changements:
            flash("Aucune modification renseignée.", "warning")
            return render_template("changer_mot_de_passe.html")

        db.session.commit()
        flash("Mise à jour réussie : " + " et ".join(changements) + ".", "success")
        return redirect(url_for("caille.dashboard"))

    return render_template("changer_mot_de_passe.html")