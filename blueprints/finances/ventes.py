"""blueprints/finances/ventes.py — Carnet de ventes général (animaux vivants, viande, sous-produits...)."""
from datetime import date, timedelta

from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import (
    Lot,
    Client,
    Vente,
)
from utils import parse_date, parse_float, parse_int
from . import bp


# ---------------------------------------------------------------------------
# VENTES (carnet de ventes général — cailles vivantes, viande, sous-produits...)
# ---------------------------------------------------------------------------
@bp.route("/ventes", methods=["GET", "POST"])
def ventes():
    if request.method == "POST":
        v = Vente(
            date_vente=parse_date(request.form.get("date_vente")),
            client_id=parse_int(request.form.get("client_id")) or None,
            lot_id=parse_int(request.form.get("lot_id")) or None,
            produit=request.form.get("produit", "").strip(),
            quantite=parse_float(request.form.get("quantite")),
            unite=request.form.get("unite", "unité"),
            prix_unitaire=parse_float(request.form.get("prix_unitaire")),
            notes=request.form.get("notes"),
        )
        if not v.produit:
            flash("Le produit vendu est obligatoire.", "danger")
        else:
            db.session.add(v)
            db.session.commit()
            flash(f"Vente de « {v.produit} » enregistrée ({v.montant_total} F).", "success")
        return redirect(url_for("finances.ventes"))

    date_debut = parse_date(request.args.get("debut"), date.today() - timedelta(days=29))
    date_fin = parse_date(request.args.get("fin"), date.today())
    entrees = Vente.query.filter(Vente.date_vente.between(date_debut, date_fin)) \
        .order_by(Vente.date_vente.desc()).all()
    total = round(sum(v.montant_total for v in entrees), 2)

    clients_tous = Client.query.order_by(Client.nom).all()
    lots_tous = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    return render_template("finances/ventes.html", entrees=entrees, clients=clients_tous, lots=lots_tous,
        total=total, date_debut=date_debut, date_fin=date_fin,
    )


@bp.route("/ventes/<int:vente_id>/supprimer", methods=["POST"])
def supprimer_vente(vente_id):
    v = Vente.query.get_or_404(vente_id)
    db.session.delete(v)
    db.session.commit()
    flash("Vente supprimée.", "info")
    return redirect(url_for("finances.ventes"))
