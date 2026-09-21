"""blueprints/personnel/employes.py — Employés de la ferme."""

from flask import render_template, request, redirect, url_for, flash

from extensions import db
from models import (
    Employe,
)
from utils import parse_date
from . import bp


# ---------------------------------------------------------------------------
# PERSONNEL
# ---------------------------------------------------------------------------
@bp.route("/personnel", methods=["GET", "POST"])
def personnel():
    if request.method == "POST":
        e = Employe(
            nom=request.form.get("nom", "").strip(),
            role=request.form.get("role"),
            telephone=request.form.get("telephone"),
            date_embauche=parse_date(request.form.get("date_embauche"), None) if request.form.get("date_embauche") else None,
            notes=request.form.get("notes"),
        )
        if not e.nom:
            flash("Le nom de l'employé est obligatoire.", "danger")
        else:
            db.session.add(e)
            db.session.commit()
            flash(f"Employé « {e.nom} » ajouté.", "success")
        return redirect(url_for("personnel.personnel"))

    liste = Employe.query.order_by(Employe.statut.desc(), Employe.nom).all()
    return render_template("personnel/personnel.html", employes=liste)


@bp.route("/personnel/<int:employe_id>/statut", methods=["POST"])
def changer_statut_employe(employe_id):
    e = Employe.query.get_or_404(employe_id)
    e.statut = "inactif" if e.statut == "actif" else "actif"
    db.session.commit()
    flash(f"{e.nom} marqué « {e.statut} ».", "info")
    return redirect(url_for("personnel.personnel"))
