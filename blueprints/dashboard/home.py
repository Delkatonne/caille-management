"""blueprints/dashboard/home.py — Tableau de bord : indicateurs du jour, alertes de provende, tâches à faire."""
from datetime import date

from flask import render_template

from models import (
    Lot,
    SuiviPonte,
    SuiviMortalite,
    TypeProvende,
    Tache,
    stock_oeufs_actuel,
)
from . import bp


# ---------------------------------------------------------------------------
# TABLEAU DE BORD
# ---------------------------------------------------------------------------
@bp.route("/")
def dashboard():
    lots_actifs = Lot.query.filter_by(statut="actif").all()
    effectif_total = sum(l.effectif_actuel for l in lots_actifs)

    today = date.today()
    ponte_jour = SuiviPonte.query.filter_by(date_jour=today).all()
    oeufs_pondus_jour = sum(p.oeufs_pondus for p in ponte_jour)
    oeufs_vendus_jour = sum(p.oeufs_vendus_total for p in ponte_jour)
    revenu_jour = round(sum(p.montant_vente for p in ponte_jour), 2)

    mortalite_jour = SuiviMortalite.query.filter_by(date_jour=today).all()
    cailles_mortes_jour = sum(m.cailles_mortes for m in mortalite_jour)
    cailletons_morts_jour = sum(m.cailletons_morts for m in mortalite_jour)

    types_provende = TypeProvende.query.filter_by(actif=True).all()
    alertes_provende = [t for t in types_provende if t.en_alerte]

    taches_a_faire = Tache.query.filter(Tache.statut != "fait").order_by(Tache.date_prevue.asc()).limit(8).all()

    return render_template("dashboard/dashboard.html",
        effectif_total=effectif_total,
        nb_lots_actifs=len(lots_actifs),
        oeufs_pondus_jour=oeufs_pondus_jour,
        oeufs_vendus_jour=oeufs_vendus_jour,
        revenu_jour=revenu_jour,
        stock_oeufs=stock_oeufs_actuel(),
        cailles_mortes_jour=cailles_mortes_jour,
        cailletons_morts_jour=cailletons_morts_jour,
        types_provende=types_provende,
        alertes_provende=alertes_provende,
        taches_a_faire=taches_a_faire,
        today=today,
    )
