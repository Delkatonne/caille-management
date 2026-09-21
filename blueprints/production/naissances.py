"""blueprints/production/naissances.py — Naissances / éclosions et achats de jeunes."""

from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import (
    Lot,
    Naissance,
)
from utils import parse_date, parse_int
from . import bp


# ---------------------------------------------------------------------------
# NAISSANCES / CAILLETONS
# ---------------------------------------------------------------------------
@bp.route("/naissances", methods=["GET", "POST"])
def naissances():
    if request.method == "POST":
        entree = Naissance(
            lot_id=parse_int(request.form.get("lot_id")),
            date_jour=parse_date(request.form.get("date_jour")),
            nombre_cailletons=parse_int(request.form.get("nombre_cailletons")),
            origine=request.form.get("origine", "eclosion"),
            notes=request.form.get("notes"),
        )
        db.session.add(entree)
        db.session.commit()
        flash("Naissance enregistrée.", "success")
        return redirect(url_for("production.naissances"))

    entrees = Naissance.query.order_by(Naissance.date_jour.desc()).limit(60).all()
    lots_actifs = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    return render_template("production/naissances.html", entrees=entrees, lots=lots_actifs)
