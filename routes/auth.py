"""
routes/auth.py — Connexion / déconnexion pour le module caille.

Un seul rôle pour l'instant (pas d'admin/employé séparés). Si HITNA a déjà
son propre système d'authentification, ce blueprint peut être retiré et
remplacé par le login existant (voir README.md).
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required

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