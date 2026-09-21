"""blueprints/stocks/provende.py — Provende (aliment) : types, achats de réapprovisionnement, consommation, alertes de stock."""
from datetime import date, timedelta

from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import (
    Lot,
    TypeProvende,
    Fournisseur,
    AchatProvende,
    ConsommationProvende,
)
from utils import parse_date, parse_float, parse_int
from . import bp


# ---------------------------------------------------------------------------
# PROVENDE : TYPES
# ---------------------------------------------------------------------------
@bp.route("/provende/types", methods=["GET", "POST"])
def types_provende():
    if request.method == "POST":
        t = TypeProvende(
            nom=request.form.get("nom", "").strip(),
            description=request.form.get("description"),
            seuil_alerte_kg=parse_float(request.form.get("seuil_alerte_kg"), 20),
        )
        if not t.nom:
            flash("Le nom du type de provende est obligatoire.", "danger")
        else:
            db.session.add(t)
            db.session.commit()
            flash(f"Type de provende « {t.nom} » ajouté.", "success")
        return redirect(url_for("stocks.types_provende"))

    types = TypeProvende.query.order_by(TypeProvende.nom).all()
    return render_template("stocks/provende_types.html", types=types)


@bp.route("/provende/types/<int:type_id>/desactiver", methods=["POST"])
def desactiver_type_provende(type_id):
    t = TypeProvende.query.get_or_404(type_id)
    t.actif = not t.actif
    db.session.commit()
    return redirect(url_for("stocks.types_provende"))


# ---------------------------------------------------------------------------
# PROVENDE : ACHATS (réapprovisionnement)
# ---------------------------------------------------------------------------
@bp.route("/provende/achats", methods=["GET", "POST"])
def achats_provende():
    if request.method == "POST":
        achat = AchatProvende(
            date_achat=parse_date(request.form.get("date_achat")),
            type_provende_id=parse_int(request.form.get("type_provende_id")),
            fournisseur_id=parse_int(request.form.get("fournisseur_id")) or None,
            quantite_kg=parse_float(request.form.get("quantite_kg")),
            prix_total=parse_float(request.form.get("prix_total")),
            notes=request.form.get("notes"),
        )
        db.session.add(achat)
        db.session.commit()
        flash(f"Achat de {achat.quantite_kg} kg enregistré.", "success")
        return redirect(url_for("stocks.achats_provende"))

    date_debut = parse_date(request.args.get("debut"), date.today() - timedelta(days=29))
    date_fin = parse_date(request.args.get("fin"), date.today())
    achats = AchatProvende.query.filter(
        AchatProvende.date_achat.between(date_debut, date_fin)
    ).order_by(AchatProvende.date_achat.desc()).all()

    totaux = {
        "kg": round(sum(a.quantite_kg for a in achats), 2),
        "cout": round(sum(a.prix_total or 0 for a in achats), 2),
    }
    types = TypeProvende.query.order_by(TypeProvende.nom).all()
    fournisseurs = Fournisseur.query.order_by(Fournisseur.nom).all()
    return render_template("stocks/provende_achats.html", achats=achats, types=types, fournisseurs=fournisseurs,
        totaux=totaux, date_debut=date_debut, date_fin=date_fin,
    )


# ---------------------------------------------------------------------------
# PROVENDE : CONSOMMATION
# ---------------------------------------------------------------------------
@bp.route("/provende/consommation", methods=["GET", "POST"])
def consommation_provende():
    if request.method == "POST":
        c = ConsommationProvende(
            date_jour=parse_date(request.form.get("date_jour")),
            lot_id=parse_int(request.form.get("lot_id")) or None,
            type_provende_id=parse_int(request.form.get("type_provende_id")),
            quantite_kg=parse_float(request.form.get("quantite_kg")),
            notes=request.form.get("notes"),
        )
        db.session.add(c)
        db.session.commit()
        flash("Consommation enregistrée.", "success")
        return redirect(url_for("stocks.consommation_provende"))

    date_debut = parse_date(request.args.get("debut"), date.today() - timedelta(days=13))
    date_fin = parse_date(request.args.get("fin"), date.today())
    consos = ConsommationProvende.query.filter(
        ConsommationProvende.date_jour.between(date_debut, date_fin)
    ).order_by(ConsommationProvende.date_jour.desc()).all()

    types = TypeProvende.query.order_by(TypeProvende.nom).all()
    lots_actifs = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    total_kg = round(sum(c.quantite_kg for c in consos), 2)
    return render_template("stocks/provende_consommation.html", consos=consos, types=types, lots=lots_actifs,
        total_kg=total_kg, date_debut=date_debut, date_fin=date_fin,
    )
