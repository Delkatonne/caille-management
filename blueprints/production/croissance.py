"""blueprints/production/croissance.py — Croissance / pesées des lots (utile pour les lots de chair)."""

from flask import render_template, request, redirect, url_for, flash, jsonify

from extensions import db
from models import (
    Lot,
    PeseeCroissance,
)
from utils import parse_date, parse_float, parse_int
from . import bp


# ---------------------------------------------------------------------------
# CROISSANCE / POIDS (lots destinés à la viande)
# ---------------------------------------------------------------------------
@bp.route("/croissance", methods=["GET", "POST"])
def croissance():
    if request.method == "POST":
        p = PeseeCroissance(
            lot_id=parse_int(request.form.get("lot_id")),
            date_pesee=parse_date(request.form.get("date_pesee")),
            poids_moyen_g=parse_float(request.form.get("poids_moyen_g")),
            nombre_pese=parse_int(request.form.get("nombre_pese")) or None,
            notes=request.form.get("notes"),
        )
        db.session.add(p)
        db.session.commit()
        flash("Pesée enregistrée.", "success")
        return redirect(url_for("production.croissance"))

    lot_filtre = request.args.get("lot_id")
    query = PeseeCroissance.query
    if lot_filtre:
        query = query.filter_by(lot_id=parse_int(lot_filtre))
    entrees = query.order_by(PeseeCroissance.date_pesee.desc()).limit(100).all()
    lots_tous = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    return render_template("production/croissance.html", entrees=entrees, lots=lots_tous, lot_filtre=lot_filtre)


@bp.route("/croissance/<int:pesee_id>/supprimer", methods=["POST"])
def supprimer_pesee(pesee_id):
    p = PeseeCroissance.query.get_or_404(pesee_id)
    db.session.delete(p)
    db.session.commit()
    flash("Pesée supprimée.", "info")
    return redirect(url_for("production.croissance"))


@bp.route("/api/stats/croissance")
def api_stats_croissance():
    lot_id = request.args.get("lot_id")
    query = PeseeCroissance.query
    if lot_id:
        query = query.filter_by(lot_id=parse_int(lot_id))
    rows = query.order_by(PeseeCroissance.date_pesee).all()
    return jsonify({
        "labels": [r.date_pesee.strftime("%d/%m/%Y") for r in rows],
        "poids": [r.poids_moyen_g for r in rows],
    })
