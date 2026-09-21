"""blueprints/personnel/taches.py — Cahier de charges : tâches, protocoles et récurrences."""
from datetime import date, timedelta

from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import (
    Lot,
    Tache,
    Employe,
)
from utils import parse_date, parse_int
from . import bp


# ---------------------------------------------------------------------------
# CAHIER DE CHARGES (tâches / protocoles)
# ---------------------------------------------------------------------------
@bp.route("/taches", methods=["GET", "POST"])
def taches():
    if request.method == "POST":
        t = Tache(
            titre=request.form.get("titre", "").strip(),
            description=request.form.get("description"),
            categorie=request.form.get("categorie", "general"),
            date_prevue=parse_date(request.form.get("date_prevue"), None) if request.form.get("date_prevue") else None,
            recurrence=request.form.get("recurrence", "aucune"),
            lot_id=parse_int(request.form.get("lot_id")) or None,
            employe_id=parse_int(request.form.get("employe_id")) or None,
            notes=request.form.get("notes"),
        )
        if not t.titre:
            flash("Le titre de la tâche est obligatoire.", "danger")
        else:
            db.session.add(t)
            db.session.commit()
            flash(f"Tâche « {t.titre} » ajoutée au cahier de charges.", "success")
        return redirect(url_for("personnel.taches"))

    filtre_statut = request.args.get("statut", "tous")
    query = Tache.query
    if filtre_statut != "tous":
        query = query.filter_by(statut=filtre_statut)
    liste = query.order_by(Tache.date_prevue.asc().nullslast()).all()
    lots_actifs = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    employes_actifs = Employe.query.filter_by(statut="actif").order_by(Employe.nom).all()
    return render_template("personnel/taches.html", taches=liste, lots=lots_actifs, employes=employes_actifs, filtre_statut=filtre_statut)


RECURRENCE_DELTA = {
    "quotidien": timedelta(days=1),
    "hebdo": timedelta(weeks=1),
    "mensuel": timedelta(days=30),
}


@bp.route("/taches/<int:tache_id>/statut", methods=["POST"])
def changer_statut_tache(tache_id):
    t = Tache.query.get_or_404(tache_id)
    nouveau_statut = request.form.get("statut", "a_faire")
    ancien_statut = t.statut
    t.statut = nouveau_statut

    if nouveau_statut == "fait":
        t.date_realisation = date.today()
        # Tâche récurrente : on programme automatiquement la prochaine échéance
        # (uniquement au moment où elle passe réellement à "fait", pas à chaque clic).
        if ancien_statut != "fait" and t.recurrence in RECURRENCE_DELTA:
            base = t.date_prevue or date.today()
            prochaine = base + RECURRENCE_DELTA[t.recurrence]
            if prochaine < date.today():
                prochaine = date.today() + RECURRENCE_DELTA[t.recurrence]
            db.session.add(Tache(
                titre=t.titre, description=t.description, categorie=t.categorie,
                date_prevue=prochaine, recurrence=t.recurrence,
                statut="a_faire", lot_id=t.lot_id, employe_id=t.employe_id, notes=t.notes,
            ))
            flash(f"Tâche récurrente : prochaine échéance programmée le {prochaine.strftime('%d/%m/%Y')}.", "info")
    else:
        t.date_realisation = None

    db.session.commit()
    return redirect(url_for("personnel.taches"))
