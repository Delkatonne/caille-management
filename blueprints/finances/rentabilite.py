"""blueprints/finances/rentabilite.py — Rentabilité : revenus - coût de la provende - dépenses, par mois et par lot."""
from datetime import date, timedelta

from flask import render_template, request, send_file

from models import (
    Lot,
    SuiviPonte,
    AchatProvende,
    Depense,
    Vente,
)
from utils import parse_date, XLSX_MIME
from services import excel_reports
from . import bp


# ---------------------------------------------------------------------------
# RENTABILITÉ (indice de consommation, revenu - coût provende)
# ---------------------------------------------------------------------------
def _donnees_rentabilite(debut_param, fin_param):
    date_debut = parse_date(debut_param, date.today() - timedelta(days=364))
    date_fin = parse_date(fin_param, date.today())

    lots_tous = Lot.query.order_by(Lot.nom).all()

    pontes = SuiviPonte.query.filter(SuiviPonte.date_jour.between(date_debut, date_fin)).all()
    ventes_periode = Vente.query.filter(Vente.date_vente.between(date_debut, date_fin)).all()
    achats = AchatProvende.query.filter(AchatProvende.date_achat.between(date_debut, date_fin)).all()
    depenses_periode = Depense.query.filter(Depense.date_depense.between(date_debut, date_fin)).all()

    mensuel = {}
    for p in pontes:
        cle = p.date_jour.strftime("%Y-%m")
        mensuel.setdefault(cle, {"revenu": 0.0, "cout_provende": 0.0, "depenses": 0.0})
        mensuel[cle]["revenu"] += p.montant_vente
    for v in ventes_periode:
        cle = v.date_vente.strftime("%Y-%m")
        mensuel.setdefault(cle, {"revenu": 0.0, "cout_provende": 0.0, "depenses": 0.0})
        mensuel[cle]["revenu"] += v.montant_total
    for a in achats:
        cle = a.date_achat.strftime("%Y-%m")
        mensuel.setdefault(cle, {"revenu": 0.0, "cout_provende": 0.0, "depenses": 0.0})
        mensuel[cle]["cout_provende"] += (a.prix_total or 0)
    for d in depenses_periode:
        cle = d.date_depense.strftime("%Y-%m")
        mensuel.setdefault(cle, {"revenu": 0.0, "cout_provende": 0.0, "depenses": 0.0})
        mensuel[cle]["depenses"] += (d.montant or 0)

    stats_mensuelles = []
    for cle in sorted(mensuel.keys()):
        r = round(mensuel[cle]["revenu"], 2)
        cp = round(mensuel[cle]["cout_provende"], 2)
        dep = round(mensuel[cle]["depenses"], 2)
        stats_mensuelles.append({
            "mois": cle, "revenu": r, "cout_provende": cp, "depenses": dep,
            "marge": round(r - cp - dep, 2),
        })

    return lots_tous, stats_mensuelles, date_debut, date_fin


@bp.route("/rentabilite")
def rentabilite():
    lots_tous, stats_mensuelles, date_debut, date_fin = _donnees_rentabilite(
        request.args.get("debut"), request.args.get("fin"))
    return render_template("finances/rentabilite.html", lots=lots_tous, stats_mensuelles=stats_mensuelles,
                            date_debut=date_debut, date_fin=date_fin)


@bp.route("/rentabilite.xlsx")
def rentabilite_excel():
    lots_tous, stats_mensuelles, date_debut, date_fin = _donnees_rentabilite(
        request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_rentabilite(lots_tous, stats_mensuelles)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"rentabilite_{date_debut}_{date_fin}.xlsx")
