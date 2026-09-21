"""blueprints/production/especes.py — Espèces et catégories d'élevage (Caille, Poule, Lapin... / Aviculture, Cuniculture...)."""

from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import (
    Lot,
    Espece,
    CategorieElevage,
    SoinSante,
    PeseeCroissance,
    TYPES_SOIN,
)
from utils import parse_int
from . import bp


# ---------------------------------------------------------------------------
# ESPÈCES / TYPES D'ÉLEVAGE (Caille, Poule, Lapin, ...)
# ---------------------------------------------------------------------------
@bp.route("/especes", methods=["GET", "POST"])
def especes():
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        if not nom:
            flash("Le nom de l'espèce est obligatoire.", "danger")
        elif Espece.query.filter_by(nom=nom).first():
            flash(f"« {nom} » existe déjà.", "danger")
        else:
            db.session.add(Espece(
                nom=nom, categorie_id=parse_int(request.form.get("categorie_id")) or None,
                description=request.form.get("description"),
            ))
            db.session.commit()
            flash(f"Espèce « {nom} » ajoutée. Vous pouvez maintenant créer des lots de ce type.", "success")
        return redirect(url_for("production.especes"))

    liste = Espece.query.order_by(Espece.nom).all()
    categories = CategorieElevage.query.order_by(CategorieElevage.nom).all()
    return render_template("production/especes.html", especes=liste, categories=categories)


@bp.route("/especes/<int:espece_id>")
def detail_espece(espece_id):
    """Fiche par animal : regroupe naissances, croissance, mortalité, ponte
    (si applicable) et santé pour tous les lots de cette espèce."""
    espece = Espece.query.get_or_404(espece_id)
    lots_espece = espece.lots.order_by(Lot.date_mise_en_place.desc()).all()
    lot_ids = [l.id for l in lots_espece]

    pond_des_oeufs = bool(espece.categorie and espece.categorie.produit_des_oeufs)

    effectif_total = sum(l.effectif_actuel for l in lots_espece if l.statut == "actif")
    mortalite_adultes = sum(l.total_mortalite_cailles for l in lots_espece)
    mortalite_jeunes = sum(l.total_mortalite_cailletons for l in lots_espece)
    naissances_total = sum(l.total_naissances for l in lots_espece)
    oeufs_pondus_total = sum(l.total_oeufs_pondus for l in lots_espece)
    revenu_total = round(sum(l.total_revenu_oeufs + l.total_revenu_ventes_diverses for l in lots_espece), 2)
    cout_provende_total = round(sum(l.cout_provende_estime for l in lots_espece), 2)
    depenses_total = round(sum(l.total_depenses for l in lots_espece), 2)
    marge_total = round(sum(l.marge_estimee for l in lots_espece), 2)

    soins_recents = SoinSante.query.filter(SoinSante.lot_id.in_(lot_ids)) \
        .order_by(SoinSante.date_soin.desc()).limit(10).all() if lot_ids else []
    pesees_recentes = PeseeCroissance.query.filter(PeseeCroissance.lot_id.in_(lot_ids)) \
        .order_by(PeseeCroissance.date_pesee.desc()).limit(10).all() if lot_ids else []

    return render_template("production/espece_detail.html", espece=espece, lots=lots_espece, pond_des_oeufs=pond_des_oeufs,
        effectif_total=effectif_total, mortalite_adultes=mortalite_adultes, mortalite_jeunes=mortalite_jeunes,
        naissances_total=naissances_total, oeufs_pondus_total=oeufs_pondus_total,
        revenu_total=revenu_total, cout_provende_total=cout_provende_total,
        depenses_total=depenses_total, marge_total=marge_total,
        soins_recents=soins_recents, pesees_recentes=pesees_recentes, types_soin=TYPES_SOIN,
    )


# ---------------------------------------------------------------------------
# CATÉGORIES D'ÉLEVAGE (Aviculture, Cuniculture, ...)
# ---------------------------------------------------------------------------
@bp.route("/categories-elevage", methods=["GET", "POST"])
def categories_elevage():
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        if not nom:
            flash("Le nom de la catégorie est obligatoire.", "danger")
        elif CategorieElevage.query.filter_by(nom=nom).first():
            flash(f"« {nom} » existe déjà.", "danger")
        else:
            db.session.add(CategorieElevage(
                nom=nom, description=request.form.get("description"),
                produit_des_oeufs=bool(request.form.get("produit_des_oeufs")),
            ))
            db.session.commit()
            flash(f"Catégorie « {nom} » ajoutée. Elle est disponible pour vos espèces.", "success")
        return redirect(url_for("production.categories_elevage"))

    liste = CategorieElevage.query.order_by(CategorieElevage.nom).all()
    return render_template("production/categories_elevage.html", categories=liste)


@bp.route("/categories-elevage/<int:categorie_id>/oeufs", methods=["POST"])
def basculer_produit_des_oeufs(categorie_id):
    c = CategorieElevage.query.get_or_404(categorie_id)
    c.produit_des_oeufs = not c.produit_des_oeufs
    db.session.commit()
    flash(f"« {c.nom} » {'produit' if c.produit_des_oeufs else 'ne produit plus'} des œufs (page Ponte).", "info")
    return redirect(url_for("production.categories_elevage"))
