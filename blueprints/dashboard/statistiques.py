"""blueprints/dashboard/statistiques.py — Statistiques : page des graphiques et API JSON (ponte, mortalité)."""
from datetime import date, timedelta

from flask import render_template, request, jsonify

from extensions import db
from models import (
    Lot,
    SuiviPonte,
    SuiviMortalite,
)
from utils import parse_date, parse_int
from . import bp


# ---------------------------------------------------------------------------
# STATISTIQUES (graphiques)
# ---------------------------------------------------------------------------
@bp.route("/statistiques")
def statistiques():
    lots_actifs = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    date_debut = date.today() - timedelta(days=29)
    date_fin = date.today()
    return render_template("dashboard/statistiques.html", lots=lots_actifs, date_debut=date_debut, date_fin=date_fin)


@bp.route("/api/stats/ponte")
def api_stats_ponte():
    date_debut = parse_date(request.args.get("debut"), date.today() - timedelta(days=29))
    date_fin = parse_date(request.args.get("fin"), date.today())
    lot_id = request.args.get("lot_id")

    query = db.session.query(
        SuiviPonte.date_jour,
        db.func.sum(SuiviPonte.oeufs_pondus),
        db.func.sum(SuiviPonte.oeufs_vendus),
    ).filter(SuiviPonte.date_jour.between(date_debut, date_fin))
    if lot_id:
        query = query.filter(SuiviPonte.lot_id == parse_int(lot_id))
    rows = query.group_by(SuiviPonte.date_jour).order_by(SuiviPonte.date_jour).all()

    return jsonify({
        "labels": [r[0].strftime("%d/%m") for r in rows],
        "pondus": [int(r[1] or 0) for r in rows],
        "vendus": [int(r[2] or 0) for r in rows],
    })


@bp.route("/api/stats/mortalite")
def api_stats_mortalite():
    date_debut = parse_date(request.args.get("debut"), date.today() - timedelta(days=29))
    date_fin = parse_date(request.args.get("fin"), date.today())
    lot_id = request.args.get("lot_id")

    query = db.session.query(
        SuiviMortalite.date_jour,
        db.func.sum(SuiviMortalite.cailles_mortes),
        db.func.sum(SuiviMortalite.cailletons_morts),
    ).filter(SuiviMortalite.date_jour.between(date_debut, date_fin))
    if lot_id:
        query = query.filter(SuiviMortalite.lot_id == parse_int(lot_id))
    rows = query.group_by(SuiviMortalite.date_jour).order_by(SuiviMortalite.date_jour).all()

    return jsonify({
        "labels": [r[0].strftime("%d/%m") for r in rows],
        "cailles": [int(r[1] or 0) for r in rows],
        "cailletons": [int(r[2] or 0) for r in rows],
    })
