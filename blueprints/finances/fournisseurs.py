"""blueprints/finances/fournisseurs.py — Fournisseurs (provende, médicaments, matériel...)."""

from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import (
    Fournisseur,
)
from . import bp


# ---------------------------------------------------------------------------
# FOURNISSEURS
# ---------------------------------------------------------------------------
@bp.route("/fournisseurs", methods=["GET", "POST"])
def fournisseurs():
    if request.method == "POST":
        f = Fournisseur(
            nom=request.form.get("nom", "").strip(),
            contact=request.form.get("contact"),
            adresse=request.form.get("adresse"),
            notes=request.form.get("notes"),
        )
        if not f.nom:
            flash("Le nom du fournisseur est obligatoire.", "danger")
        else:
            db.session.add(f)
            db.session.commit()
            flash(f"Fournisseur « {f.nom} » ajouté.", "success")
        return redirect(url_for("finances.fournisseurs"))

    liste = Fournisseur.query.order_by(Fournisseur.nom).all()
    return render_template("finances/fournisseurs.html", fournisseurs=liste)
