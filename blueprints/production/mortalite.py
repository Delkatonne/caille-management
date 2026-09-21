"""blueprints/production/mortalite.py — Mortalité quotidienne (adultes et jeunes)."""
from datetime import date, timedelta

from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import (
    Lot,
    SuiviMortalite,
)
from utils import parse_date, parse_int
from . import bp


# ---------------------------------------------------------------------------
# MORTALITÉ
# ---------------------------------------------------------------------------
@bp.route("/mortalite", methods=["GET", "POST"])
def mortalite():
    if request.method == "POST":
        lot_id = parse_int(request.form.get("lot_id"))
        date_jour = parse_date(request.form.get("date_jour"))
        entree = SuiviMortalite.query.filter_by(lot_id=lot_id, date_jour=date_jour).first()
        if entree is None:
            entree = SuiviMortalite(lot_id=lot_id, date_jour=date_jour)
            db.session.add(entree)
        entree.cailles_mortes = parse_int(request.form.get("cailles_mortes"))
        entree.cailletons_morts = parse_int(request.form.get("cailletons_morts"))
        entree.cause = request.form.get("cause")
        entree.notes = request.form.get("notes")
        db.session.commit()
        flash("Mortalité du jour enregistrée.", "success")
        return redirect(url_for("production.mortalite"))

    date_debut = parse_date(request.args.get("debut"), date.today() - timedelta(days=13))
    date_fin = parse_date(request.args.get("fin"), date.today())
    entrees = SuiviMortalite.query.filter(
        SuiviMortalite.date_jour.between(date_debut, date_fin)
    ).order_by(SuiviMortalite.date_jour.desc()).all()

    totaux = {
        "cailles": sum(e.cailles_mortes for e in entrees),
        "cailletons": sum(e.cailletons_morts for e in entrees),
    }
    lots_actifs = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    return render_template("production/mortalite.html", entrees=entrees, lots=lots_actifs, totaux=totaux,
        date_debut=date_debut, date_fin=date_fin,
    )
