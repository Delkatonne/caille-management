"""blueprints/production/lots.py — Lots (bandes d'animaux) : création, modification, archivage, fiche détaillée."""
from datetime import date

from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import (
    Lot,
    SuiviPonte,
    SuiviMortalite,
    Naissance,
    Espece,
    SoinSante,
    PeseeCroissance,
    TYPES_SOIN,
)
from utils import parse_date, parse_int
from . import bp


# ---------------------------------------------------------------------------
# LOTS
# ---------------------------------------------------------------------------
@bp.route("/lots", methods=["GET", "POST"])
def lots():
    if request.method == "POST":
        lot = Lot(
            nom=request.form.get("nom", "").strip(),
            espece_id=parse_int(request.form.get("espece_id")) or None,
            type_lot=request.form.get("type_lot", "ponte"),
            date_mise_en_place=parse_date(request.form.get("date_mise_en_place")),
            effectif_initial=parse_int(request.form.get("effectif_initial")),
            notes=request.form.get("notes"),
        )
        if not lot.nom:
            flash("Le nom du lot est obligatoire.", "danger")
        else:
            db.session.add(lot)
            db.session.commit()
            flash(f"Lot « {lot.nom} » créé.", "success")
        return redirect(url_for("production.lots"))

    filtre_statut = request.args.get("statut", "actif")
    query = Lot.query
    if filtre_statut != "tous":
        query = query.filter_by(statut=filtre_statut)
    liste_lots = query.order_by(Lot.date_mise_en_place.desc()).all()
    especes = Espece.query.order_by(Espece.nom).all()
    return render_template("production/lots.html", lots=liste_lots, filtre_statut=filtre_statut, especes=especes)


@bp.route("/lots/<int:lot_id>/modifier", methods=["POST"])
def modifier_lot(lot_id):
    lot = Lot.query.get_or_404(lot_id)
    lot.nom = request.form.get("nom", lot.nom).strip()
    lot.espece_id = parse_int(request.form.get("espece_id")) or None
    lot.type_lot = request.form.get("type_lot", lot.type_lot)
    lot.date_mise_en_place = parse_date(request.form.get("date_mise_en_place"), lot.date_mise_en_place)
    lot.effectif_initial = parse_int(request.form.get("effectif_initial"), lot.effectif_initial)
    lot.notes = request.form.get("notes")
    db.session.commit()
    flash(f"Lot « {lot.nom} » mis à jour.", "success")
    return redirect(url_for("production.lots"))


@bp.route("/lots/<int:lot_id>/archiver", methods=["POST"])
def archiver_lot(lot_id):
    lot = Lot.query.get_or_404(lot_id)
    lot.statut = "archive"
    lot.date_reforme = date.today()
    db.session.commit()
    flash(f"Lot « {lot.nom} » archivé (réformé).", "info")
    return redirect(url_for("production.lots"))


@bp.route("/lots/<int:lot_id>/reactiver", methods=["POST"])
def reactiver_lot(lot_id):
    lot = Lot.query.get_or_404(lot_id)
    lot.statut = "actif"
    lot.date_reforme = None
    db.session.commit()
    flash(f"Lot « {lot.nom} » réactivé.", "info")
    return redirect(url_for("production.lots"))


@bp.route("/lots/<int:lot_id>")
def detail_lot(lot_id):
    lot = Lot.query.get_or_404(lot_id)
    pontes = lot.pontes.order_by(SuiviPonte.date_jour.desc()).limit(30).all()
    mortalites = lot.mortalites.order_by(SuiviMortalite.date_jour.desc()).limit(30).all()
    naissances = lot.naissances.order_by(Naissance.date_jour.desc()).limit(30).all()
    soins = SoinSante.query.filter_by(lot_id=lot.id).order_by(SoinSante.date_soin.desc()).limit(20).all()
    pesees = PeseeCroissance.query.filter_by(lot_id=lot.id).order_by(PeseeCroissance.date_pesee.desc()).limit(20).all()
    return render_template("production/lot_detail.html", lot=lot, pontes=pontes, mortalites=mortalites,
                            naissances=naissances, soins=soins, pesees=pesees, types_soin=TYPES_SOIN)


# ---------------------------------------------------------------------------
# ARCHIVE
# ---------------------------------------------------------------------------
@bp.route("/archive")
def archive():
    lots_archives = Lot.query.filter_by(statut="archive").order_by(Lot.date_reforme.desc()).all()
    return render_template("production/archive.html", lots=lots_archives)
