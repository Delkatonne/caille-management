"""blueprints/finances/depenses.py — Dépenses diverses (vaccination, médicament, transport, matériel...)."""
from datetime import date, timedelta

from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import (
    Lot,
    Depense,
)
from utils import parse_date, parse_float, parse_int
from . import bp


# ---------------------------------------------------------------------------
# DÉPENSES DIVERSES (vaccination, médicament, transport, matériel...)
# ---------------------------------------------------------------------------
CATEGORIES_DEPENSE_SUGGESTIONS = [
    "Vaccination", "Médicament", "Alimentation complémentaire",
    "Transport", "Matériel", "Main d'œuvre", "Entretien", "Autre",
]


@bp.route("/depenses", methods=["GET", "POST"])
def depenses():
    if request.method == "POST":
        categorie = request.form.get("categorie", "").strip()
        d = Depense(
            date_depense=parse_date(request.form.get("date_depense")),
            categorie=categorie,
            montant=parse_float(request.form.get("montant")),
            lot_id=parse_int(request.form.get("lot_id")) or None,
            notes=request.form.get("notes"),
        )
        if not categorie:
            flash("La catégorie de la dépense est obligatoire (ex: Vaccination, Transport...).", "danger")
        else:
            db.session.add(d)
            db.session.commit()
            flash(f"Dépense « {categorie} » de {d.montant} F enregistrée.", "success")
        return redirect(url_for("finances.depenses"))

    date_debut = parse_date(request.args.get("debut"), date.today() - timedelta(days=29))
    date_fin = parse_date(request.args.get("fin"), date.today())
    entrees = Depense.query.filter(Depense.date_depense.between(date_debut, date_fin)) \
        .order_by(Depense.date_depense.desc()).all()
    total = round(sum(d.montant for d in entrees), 2)

    lots_tous = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    return render_template("finances/depenses.html", entrees=entrees, lots=lots_tous, total=total,
        date_debut=date_debut, date_fin=date_fin,
        suggestions=CATEGORIES_DEPENSE_SUGGESTIONS,
    )


@bp.route("/depenses/<int:depense_id>/supprimer", methods=["POST"])
def supprimer_depense(depense_id):
    d = Depense.query.get_or_404(depense_id)
    db.session.delete(d)
    db.session.commit()
    flash("Dépense supprimée.", "info")
    return redirect(url_for("finances.depenses"))
