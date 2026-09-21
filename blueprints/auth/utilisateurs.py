"""blueprints/auth/utilisateurs.py — Gestion des comptes (réservée au propriétaire)."""
from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user

from extensions import db
from models import User
from permissions import LIBELLES, ROLES
from . import bp


@bp.route("/utilisateurs", methods=["GET", "POST"])
def utilisateurs():
    if request.method == "POST":
        identifiant = request.form.get("username", "").strip()
        mot_de_passe = request.form.get("mot_de_passe", "")
        role = request.form.get("role", "")
        if not identifiant:
            flash("L'identifiant est obligatoire.", "danger")
        elif role not in ROLES:
            flash("Rôle invalide.", "danger")
        elif len(mot_de_passe) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères.", "danger")
        elif User.query.filter_by(username=identifiant).first():
            flash("Cet identifiant est déjà utilisé.", "danger")
        else:
            u = User(username=identifiant, role=role, actif=True)
            u.set_password(mot_de_passe)
            db.session.add(u)
            db.session.commit()
            flash(f"Compte « {identifiant} » créé ({LIBELLES[role]}).", "success")
        return redirect(url_for("auth.utilisateurs"))

    liste = User.query.order_by(User.actif.desc(), User.username).all()
    return render_template("auth/utilisateurs.html", utilisateurs=liste, libelles=LIBELLES)


@bp.route("/utilisateurs/<int:user_id>/role", methods=["POST"])
def changer_role_utilisateur(user_id):
    u = User.query.get_or_404(user_id)
    role = request.form.get("role", "")
    if role not in ROLES:
        flash("Rôle invalide.", "danger")
    elif u.id == current_user.id:
        # Le propriétaire connecté ne peut pas se rétrograder : il resterait sans propriétaire.
        flash("Vous ne pouvez pas modifier votre propre rôle.", "warning")
    else:
        u.role = role
        db.session.commit()
        flash(f"« {u.username} » est maintenant {LIBELLES[role]}.", "success")
    return redirect(url_for("auth.utilisateurs"))


@bp.route("/utilisateurs/<int:user_id>/actif", methods=["POST"])
def basculer_actif_utilisateur(user_id):
    u = User.query.get_or_404(user_id)
    if u.id == current_user.id:
        flash("Vous ne pouvez pas désactiver votre propre compte.", "warning")
    else:
        u.actif = not u.actif
        db.session.commit()
        flash(f"Compte « {u.username} » {'réactivé' if u.actif else 'désactivé'}.", "success")
    return redirect(url_for("auth.utilisateurs"))


@bp.route("/utilisateurs/<int:user_id>/mot-de-passe", methods=["POST"])
def reinitialiser_mot_de_passe(user_id):
    u = User.query.get_or_404(user_id)
    nouveau = request.form.get("nouveau_mot_de_passe", "")
    if len(nouveau) < 6:
        flash("Le mot de passe doit contenir au moins 6 caractères.", "danger")
    else:
        u.set_password(nouveau)
        db.session.commit()
        flash(f"Mot de passe de « {u.username} » réinitialisé.", "success")
    return redirect(url_for("auth.utilisateurs"))
