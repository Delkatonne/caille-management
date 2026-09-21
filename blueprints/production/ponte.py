"""blueprints/production/ponte.py — Ponte quotidienne et ventes rapides d'œufs."""
from datetime import date, timedelta

from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import (
    Lot,
    SuiviPonte,
    Espece,
    CategorieElevage,
    stock_oeufs_actuel,
)
from utils import parse_date, parse_float, parse_int
from . import bp


# ---------------------------------------------------------------------------
# PONTE / VENTE D'ŒUFS
# ---------------------------------------------------------------------------
@bp.route("/ponte", methods=["GET", "POST"])
def ponte():
    lots_pondeurs = Lot.query.join(Espece, Lot.espece_id == Espece.id) \
        .join(CategorieElevage, Espece.categorie_id == CategorieElevage.id) \
        .filter(Lot.statut != "archive", CategorieElevage.produit_des_oeufs.is_(True)) \
        .order_by(Lot.nom).all()
    ids_lots_pondeurs = {l.id for l in lots_pondeurs}

    if request.method == "POST":
        lot_id = parse_int(request.form.get("lot_id"))
        if lot_id not in ids_lots_pondeurs:
            flash("Ce lot n'appartient pas à une espèce productrice d'œufs (voir Catégories d'élevage).", "danger")
            return redirect(url_for("production.ponte"))
        date_jour = parse_date(request.form.get("date_jour"))
        entree = SuiviPonte.query.filter_by(lot_id=lot_id, date_jour=date_jour).first()
        if entree is None:
            entree = SuiviPonte(lot_id=lot_id, date_jour=date_jour)
            db.session.add(entree)
        entree.oeufs_pondus = parse_int(request.form.get("oeufs_pondus"))
        entree.oeufs_vendus = parse_int(request.form.get("oeufs_vendus"))
        entree.prix_unitaire_vente = parse_float(request.form.get("prix_unitaire_vente"))
        entree.plateaux_vendus = parse_int(request.form.get("plateaux_vendus"))
        entree.prix_plateau_vente = parse_float(request.form.get("prix_plateau_vente"))
        entree.oeufs_casses = parse_int(request.form.get("oeufs_casses"))
        entree.oeufs_autoconsommes = parse_int(request.form.get("oeufs_autoconsommes"))
        entree.notes = request.form.get("notes")
        db.session.commit()
        flash("Entrée de ponte enregistrée.", "success")
        return redirect(url_for("production.ponte"))

    date_debut = parse_date(request.args.get("debut"), date.today() - timedelta(days=13))
    date_fin = parse_date(request.args.get("fin"), date.today())
    query = SuiviPonte.query.filter(SuiviPonte.date_jour.between(date_debut, date_fin))
    lot_filtre = request.args.get("lot_id")
    if lot_filtre:
        query = query.filter_by(lot_id=parse_int(lot_filtre))
    elif ids_lots_pondeurs:
        query = query.filter(SuiviPonte.lot_id.in_(ids_lots_pondeurs))
    else:
        query = query.filter(SuiviPonte.id == -1)  # aucun lot pondeur -> aucun résultat
    entrees = query.order_by(SuiviPonte.date_jour.desc()).all()

    totaux = {
        "pondus": sum(e.oeufs_pondus for e in entrees),
        "vendus": sum(e.oeufs_vendus_total for e in entrees),
        "casses": sum(e.oeufs_casses for e in entrees),
        "revenu": round(sum(e.montant_vente for e in entrees), 2),
    }

    return render_template("production/ponte.html", entrees=entrees, lots=lots_pondeurs, totaux=totaux,
        date_debut=date_debut, date_fin=date_fin, lot_filtre=lot_filtre,
        stock_oeufs=stock_oeufs_actuel(), taille_plateau=SuiviPonte.TAILLE_PLATEAU,
    )


@bp.route("/ponte/<int:entree_id>/supprimer", methods=["POST"])
def supprimer_ponte(entree_id):
    entree = SuiviPonte.query.get_or_404(entree_id)
    db.session.delete(entree)
    db.session.commit()
    flash("Entrée de ponte supprimée.", "info")
    return redirect(url_for("production.ponte"))
