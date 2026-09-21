"""blueprints/dashboard/rapports.py — Rapports PDF et Excel (ponte, mortalité, provende, ventes, dépenses, santé...)."""
from datetime import date, timedelta

from flask import render_template, request, send_file

from models import (
    Lot,
    SuiviPonte,
    SuiviMortalite,
    Naissance,
    Fournisseur,
    AchatProvende,
    ConsommationProvende,
    Tache,
    Depense,
    Employe,
    SoinSante,
    Client,
    Vente,
    PeseeCroissance,
    TYPES_SOIN,
)
from utils import parse_date, parse_int, XLSX_MIME
from services import reports, excel_reports
from . import bp


# ---------------------------------------------------------------------------
# RAPPORTS (PDF + Excel)
# ---------------------------------------------------------------------------
@bp.route("/rapports")
def rapports():
    lots_tous = Lot.query.order_by(Lot.nom).all()
    date_debut = date.today() - timedelta(days=29)
    date_fin = date.today()
    return render_template("dashboard/rapports.html", lots=lots_tous, date_debut=date_debut, date_fin=date_fin)


# ---- Fonctions internes de préparation des données (partagées PDF / Excel) ----
def _donnees_ponte(debut_param, fin_param):
    date_debut = parse_date(debut_param, date.today() - timedelta(days=29))
    date_fin = parse_date(fin_param, date.today())
    entrees = SuiviPonte.query.filter(SuiviPonte.date_jour.between(date_debut, date_fin)) \
        .order_by(SuiviPonte.date_jour).all()
    totaux = {
        "pondus": sum(e.oeufs_pondus for e in entrees),
        "vendus": sum(e.oeufs_vendus for e in entrees),
        "casses": sum(e.oeufs_casses for e in entrees),
        "revenu": round(sum(e.montant_vente for e in entrees), 2),
    }
    return entrees, date_debut, date_fin, totaux


def _donnees_mortalite(debut_param, fin_param):
    date_debut = parse_date(debut_param, date.today() - timedelta(days=29))
    date_fin = parse_date(fin_param, date.today())
    entrees = SuiviMortalite.query.filter(SuiviMortalite.date_jour.between(date_debut, date_fin)) \
        .order_by(SuiviMortalite.date_jour).all()
    totaux = {
        "cailles": sum(e.cailles_mortes for e in entrees),
        "cailletons": sum(e.cailletons_morts for e in entrees),
    }
    return entrees, date_debut, date_fin, totaux


def _donnees_achats(debut_param, fin_param):
    date_debut = parse_date(debut_param, date.today() - timedelta(days=29))
    date_fin = parse_date(fin_param, date.today())
    achats = AchatProvende.query.filter(AchatProvende.date_achat.between(date_debut, date_fin)) \
        .order_by(AchatProvende.date_achat).all()
    totaux = {
        "kg": round(sum(a.quantite_kg for a in achats), 2),
        "cout": round(sum(a.prix_total or 0 for a in achats), 2),
    }
    return achats, date_debut, date_fin, totaux


def _donnees_naissances(debut_param, fin_param):
    date_debut = parse_date(debut_param, date.today() - timedelta(days=29))
    date_fin = parse_date(fin_param, date.today())
    entrees = Naissance.query.filter(Naissance.date_jour.between(date_debut, date_fin)) \
        .order_by(Naissance.date_jour).all()
    total = sum(e.nombre_cailletons for e in entrees)
    return entrees, date_debut, date_fin, total


def _donnees_consommation(debut_param, fin_param):
    date_debut = parse_date(debut_param, date.today() - timedelta(days=29))
    date_fin = parse_date(fin_param, date.today())
    entrees = ConsommationProvende.query.filter(ConsommationProvende.date_jour.between(date_debut, date_fin)) \
        .order_by(ConsommationProvende.date_jour).all()
    total_kg = round(sum(e.quantite_kg for e in entrees), 2)
    return entrees, date_debut, date_fin, total_kg


def _donnees_taches(filtre_statut):
    query = Tache.query
    if filtre_statut != "tous":
        query = query.filter_by(statut=filtre_statut)
    return query.order_by(Tache.date_prevue.asc().nullslast()).all()


def _donnees_depenses(debut_param, fin_param):
    date_debut = parse_date(debut_param, date.today() - timedelta(days=29))
    date_fin = parse_date(fin_param, date.today())
    entrees = Depense.query.filter(Depense.date_depense.between(date_debut, date_fin)) \
        .order_by(Depense.date_depense).all()
    total = round(sum(d.montant for d in entrees), 2)
    return entrees, date_debut, date_fin, total


def _donnees_lot(lot_id, debut_param, fin_param):
    lot = Lot.query.get_or_404(lot_id)
    pontes_q = lot.pontes.order_by(SuiviPonte.date_jour)
    mortalites_q = lot.mortalites.order_by(SuiviMortalite.date_jour)
    naissances_q = lot.naissances.order_by(Naissance.date_jour)

    if debut_param or fin_param:
        date_debut = parse_date(debut_param, date(1900, 1, 1))
        date_fin = parse_date(fin_param, date.today())
        pontes_q = pontes_q.filter(SuiviPonte.date_jour.between(date_debut, date_fin))
        mortalites_q = mortalites_q.filter(SuiviMortalite.date_jour.between(date_debut, date_fin))
        naissances_q = naissances_q.filter(Naissance.date_jour.between(date_debut, date_fin))

    return lot, pontes_q.all(), mortalites_q.all(), naissances_q.all()


# ---- Ponte ----
@bp.route("/rapports/ponte.pdf")
def rapport_ponte_pdf():
    entrees, date_debut, date_fin, totaux = _donnees_ponte(request.args.get("debut"), request.args.get("fin"))
    buf = reports.rapport_ponte(entrees, date_debut, date_fin, totaux)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"rapport_ponte_{date_debut}_{date_fin}.pdf")


@bp.route("/rapports/ponte.xlsx")
def rapport_ponte_excel():
    entrees, date_debut, date_fin, totaux = _donnees_ponte(request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_ponte(entrees, totaux)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"rapport_ponte_{date_debut}_{date_fin}.xlsx")


# ---- Mortalité ----
@bp.route("/rapports/mortalite.pdf")
def rapport_mortalite_pdf():
    entrees, date_debut, date_fin, totaux = _donnees_mortalite(request.args.get("debut"), request.args.get("fin"))
    buf = reports.rapport_mortalite(entrees, date_debut, date_fin, totaux)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"rapport_mortalite_{date_debut}_{date_fin}.pdf")


@bp.route("/rapports/mortalite.xlsx")
def rapport_mortalite_excel():
    entrees, date_debut, date_fin, totaux = _donnees_mortalite(request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_mortalite(entrees, totaux)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"rapport_mortalite_{date_debut}_{date_fin}.xlsx")


# ---- Achats de provende ----
@bp.route("/rapports/achats.pdf")
def rapport_achats_pdf():
    achats, date_debut, date_fin, totaux = _donnees_achats(request.args.get("debut"), request.args.get("fin"))
    buf = reports.rapport_achats(achats, date_debut, date_fin, totaux)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"rapport_achats_provende_{date_debut}_{date_fin}.pdf")


@bp.route("/rapports/achats.xlsx")
def rapport_achats_excel():
    achats, date_debut, date_fin, totaux = _donnees_achats(request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_achats(achats, totaux)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"rapport_achats_provende_{date_debut}_{date_fin}.xlsx")


# ---- Fiche d'un lot ----
@bp.route("/rapports/lot/<int:lot_id>.pdf")
def rapport_lot_pdf(lot_id):
    lot, pontes, mortalites, naissances = _donnees_lot(lot_id, request.args.get("debut"), request.args.get("fin"))
    buf = reports.fiche_lot(lot, pontes, mortalites, naissances)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"fiche_{lot.nom}.pdf")


@bp.route("/rapports/lot/<int:lot_id>.xlsx")
def rapport_lot_excel(lot_id):
    lot, pontes, mortalites, naissances = _donnees_lot(lot_id, request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_lot(lot, pontes, mortalites, naissances)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"fiche_{lot.nom}.xlsx")


# ---- Naissances ----
@bp.route("/rapports/naissances.pdf")
def rapport_naissances_pdf():
    entrees, date_debut, date_fin, total = _donnees_naissances(request.args.get("debut"), request.args.get("fin"))
    buf = reports.rapport_naissances(entrees, date_debut, date_fin, total)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"rapport_naissances_{date_debut}_{date_fin}.pdf")


@bp.route("/rapports/naissances.xlsx")
def rapport_naissances_excel():
    entrees, date_debut, date_fin, total = _donnees_naissances(request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_naissances(entrees, total)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"rapport_naissances_{date_debut}_{date_fin}.xlsx")


# ---- Consommation de provende ----
@bp.route("/rapports/consommation.pdf")
def rapport_consommation_pdf():
    entrees, date_debut, date_fin, total_kg = _donnees_consommation(request.args.get("debut"), request.args.get("fin"))
    buf = reports.rapport_consommation(entrees, date_debut, date_fin, total_kg)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"rapport_consommation_{date_debut}_{date_fin}.pdf")


@bp.route("/rapports/consommation.xlsx")
def rapport_consommation_excel():
    entrees, date_debut, date_fin, total_kg = _donnees_consommation(request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_consommation(entrees, total_kg)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"rapport_consommation_{date_debut}_{date_fin}.xlsx")


# ---- Cahier de charges ----
@bp.route("/rapports/taches.pdf")
def rapport_taches_pdf():
    filtre_statut = request.args.get("statut", "tous")
    taches_liste = _donnees_taches(filtre_statut)
    buf = reports.rapport_taches(taches_liste, filtre_statut)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"cahier_de_charges_{filtre_statut}.pdf")


@bp.route("/rapports/taches.xlsx")
def rapport_taches_excel():
    filtre_statut = request.args.get("statut", "tous")
    taches_liste = _donnees_taches(filtre_statut)
    buf = excel_reports.excel_taches(taches_liste)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"cahier_de_charges_{filtre_statut}.xlsx")


# ---- Fournisseurs ----
@bp.route("/rapports/fournisseurs.pdf")
def rapport_fournisseurs_pdf():
    liste = Fournisseur.query.order_by(Fournisseur.nom).all()
    buf = reports.rapport_fournisseurs(liste)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name="fournisseurs.pdf")


@bp.route("/rapports/fournisseurs.xlsx")
def rapport_fournisseurs_excel():
    liste = Fournisseur.query.order_by(Fournisseur.nom).all()
    buf = excel_reports.excel_fournisseurs(liste)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name="fournisseurs.xlsx")


# ---- Dépenses diverses ----
@bp.route("/rapports/depenses.pdf")
def rapport_depenses_pdf():
    entrees, date_debut, date_fin, total = _donnees_depenses(request.args.get("debut"), request.args.get("fin"))
    buf = reports.rapport_depenses(entrees, date_debut, date_fin, total)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"rapport_depenses_{date_debut}_{date_fin}.pdf")


@bp.route("/rapports/depenses.xlsx")
def rapport_depenses_excel():
    entrees, date_debut, date_fin, total = _donnees_depenses(request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_depenses(entrees, total)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"rapport_depenses_{date_debut}_{date_fin}.xlsx")


# ---- Personnel ----
@bp.route("/rapports/personnel.pdf")
def rapport_personnel_pdf():
    liste = Employe.query.order_by(Employe.statut.desc(), Employe.nom).all()
    buf = reports.rapport_personnel(liste)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="personnel.pdf")


@bp.route("/rapports/personnel.xlsx")
def rapport_personnel_excel():
    liste = Employe.query.order_by(Employe.statut.desc(), Employe.nom).all()
    buf = excel_reports.excel_personnel(liste)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True, download_name="personnel.xlsx")


# ---- Santé ----
def _donnees_sante(debut_param, fin_param):
    date_debut = parse_date(debut_param, date.today() - timedelta(days=89))
    date_fin = parse_date(fin_param, date.today())
    entrees = SoinSante.query.filter(SoinSante.date_soin.between(date_debut, date_fin)) \
        .order_by(SoinSante.date_soin).all()
    return entrees, date_debut, date_fin


@bp.route("/rapports/sante.pdf")
def rapport_sante_pdf():
    entrees, date_debut, date_fin = _donnees_sante(request.args.get("debut"), request.args.get("fin"))
    buf = reports.rapport_sante(entrees, date_debut, date_fin, TYPES_SOIN)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"carnet_sante_{date_debut}_{date_fin}.pdf")


@bp.route("/rapports/sante.xlsx")
def rapport_sante_excel():
    entrees, date_debut, date_fin = _donnees_sante(request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_sante(entrees, TYPES_SOIN)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"carnet_sante_{date_debut}_{date_fin}.xlsx")


# ---- Clients ----
@bp.route("/rapports/clients.pdf")
def rapport_clients_pdf():
    liste = Client.query.order_by(Client.nom).all()
    buf = reports.rapport_clients(liste)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="clients.pdf")


@bp.route("/rapports/clients.xlsx")
def rapport_clients_excel():
    liste = Client.query.order_by(Client.nom).all()
    buf = excel_reports.excel_clients(liste)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True, download_name="clients.xlsx")


# ---- Ventes ----
def _donnees_ventes(debut_param, fin_param):
    date_debut = parse_date(debut_param, date.today() - timedelta(days=29))
    date_fin = parse_date(fin_param, date.today())
    entrees = Vente.query.filter(Vente.date_vente.between(date_debut, date_fin)) \
        .order_by(Vente.date_vente).all()
    total = round(sum(v.montant_total for v in entrees), 2)
    return entrees, date_debut, date_fin, total


@bp.route("/rapports/ventes.pdf")
def rapport_ventes_pdf():
    entrees, date_debut, date_fin, total = _donnees_ventes(request.args.get("debut"), request.args.get("fin"))
    buf = reports.rapport_ventes(entrees, date_debut, date_fin, total)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"rapport_ventes_{date_debut}_{date_fin}.pdf")


@bp.route("/rapports/ventes.xlsx")
def rapport_ventes_excel():
    entrees, date_debut, date_fin, total = _donnees_ventes(request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_ventes(entrees, total)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"rapport_ventes_{date_debut}_{date_fin}.xlsx")


# ---- Croissance ----
@bp.route("/rapports/croissance.pdf")
def rapport_croissance_pdf():
    lot_id = request.args.get("lot_id")
    query = PeseeCroissance.query
    lot_nom = None
    if lot_id:
        query = query.filter_by(lot_id=parse_int(lot_id))
        lot = Lot.query.get(parse_int(lot_id))
        lot_nom = lot.nom if lot else None
    entrees = query.order_by(PeseeCroissance.date_pesee).all()
    buf = reports.rapport_croissance(entrees, lot_nom)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="suivi_croissance.pdf")


@bp.route("/rapports/croissance.xlsx")
def rapport_croissance_excel():
    lot_id = request.args.get("lot_id")
    query = PeseeCroissance.query
    if lot_id:
        query = query.filter_by(lot_id=parse_int(lot_id))
    entrees = query.order_by(PeseeCroissance.date_pesee).all()
    buf = excel_reports.excel_croissance(entrees)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True, download_name="suivi_croissance.xlsx")
