"""blueprints/finances/clients.py — Carnet de clients."""

from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import (
    Client,
)
from . import bp


# ---------------------------------------------------------------------------
# CLIENTS
# ---------------------------------------------------------------------------
@bp.route("/clients", methods=["GET", "POST"])
def clients():
    if request.method == "POST":
        c = Client(
            nom=request.form.get("nom", "").strip(),
            telephone=request.form.get("telephone"),
            adresse=request.form.get("adresse"),
            notes=request.form.get("notes"),
        )
        if not c.nom:
            flash("Le nom du client est obligatoire.", "danger")
        else:
            db.session.add(c)
            db.session.commit()
            flash(f"Client « {c.nom} » ajouté.", "success")
        return redirect(url_for("finances.clients"))

    liste = Client.query.order_by(Client.nom).all()
    return render_template("finances/clients.html", clients=liste)
