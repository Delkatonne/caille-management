"""blueprints/production/sante.py — Suivi sanitaire : vaccinations, traitements, maladies, visites vétérinaires."""
from datetime import date, timedelta

from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import (
    Lot,
    Employe,
    SoinSante,
    TYPES_SOIN,
)
from utils import parse_date, parse_int
from . import bp


# ---------------------------------------------------------------------------
# SUIVI SANITAIRE (vaccinations, traitements, maladies)
# ---------------------------------------------------------------------------
@bp.route("/sante", methods=["GET", "POST"])
def sante():
    if request.method == "POST":
        s = SoinSante(
            lot_id=parse_int(request.form.get("lot_id")),
            date_soin=parse_date(request.form.get("date_soin")),
            type_soin=request.form.get("type_soin", "vaccination"),
            produit=request.form.get("produit"),
            employe_id=parse_int(request.form.get("employe_id")) or None,
            notes=request.form.get("notes"),
        )
        db.session.add(s)
        db.session.commit()
        flash("Soin de santé enregistré.", "success")
        return redirect(url_for("production.sante"))

    date_debut = parse_date(request.args.get("debut"), date.today() - timedelta(days=89))
    date_fin = parse_date(request.args.get("fin"), date.today())
    entrees = SoinSante.query.filter(SoinSante.date_soin.between(date_debut, date_fin)) \
        .order_by(SoinSante.date_soin.desc()).all()

    lots_tous = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    employes_actifs = Employe.query.filter_by(statut="actif").order_by(Employe.nom).all()
    return render_template("production/sante.html", entrees=entrees, lots=lots_tous, employes=employes_actifs,
        types_soin=TYPES_SOIN, date_debut=date_debut, date_fin=date_fin,
    )


@bp.route("/sante/<int:soin_id>/supprimer", methods=["POST"])
def supprimer_soin(soin_id):
    s = SoinSante.query.get_or_404(soin_id)
    db.session.delete(s)
    db.session.commit()
    flash("Soin supprimé.", "info")
    return redirect(url_for("production.sante"))
