"""
routes/caille.py — Blueprint Flask du module "Gestion de caille"

INTEGRATION DANS HITNA :
Dans votre app.py principal, ajoutez :

    from routes.caille import caille_bp
    app.register_blueprint(caille_bp)

Toutes les URL du module sont préfixées /caille (ex: /caille/lots).
Si votre app utilise déjà @login_required (flask-login) sur les autres
routes, ajoutez le même décorateur sur les fonctions ci-dessous pour
protéger ce module derrière l'authentification existante.
"""
from datetime import date, datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user

from extensions import db, login_manager
from models import (
    Lot, SuiviPonte, SuiviMortalite, Naissance,
    TypeProvende, Fournisseur, AchatProvende, ConsommationProvende,
    Tache, Espece, CategorieElevage, Depense, Employe, SoinSante, Client, Vente, PeseeCroissance,
    stock_oeufs_actuel,
)
import reports
import excel_reports

caille_bp = Blueprint(
    "caille", __name__,
    url_prefix="/caille",
    template_folder="../templates/caille",
    static_folder="../static/caille",
)


@caille_bp.before_request
def _exiger_connexion():
    """Protège toutes les routes du module derrière une connexion, sauf les
    fichiers statiques (CSS) qui doivent rester accessibles depuis la page
    de connexion elle-même."""
    if request.endpoint == "caille.static":
        return None
    if not current_user.is_authenticated:
        return login_manager.unauthorized()


def _parse_date(value, default=None):
    if not value:
        return default or date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default or date.today()


def _parse_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# TABLEAU DE BORD
# ---------------------------------------------------------------------------
@caille_bp.route("/")
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

    return render_template(
        "dashboard.html",
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


# ---------------------------------------------------------------------------
# LOTS
# ---------------------------------------------------------------------------
@caille_bp.route("/lots", methods=["GET", "POST"])
def lots():
    if request.method == "POST":
        lot = Lot(
            nom=request.form.get("nom", "").strip(),
            espece_id=_parse_int(request.form.get("espece_id")) or None,
            type_lot=request.form.get("type_lot", "ponte"),
            date_mise_en_place=_parse_date(request.form.get("date_mise_en_place")),
            effectif_initial=_parse_int(request.form.get("effectif_initial")),
            notes=request.form.get("notes"),
        )
        if not lot.nom:
            flash("Le nom du lot est obligatoire.", "danger")
        else:
            db.session.add(lot)
            db.session.commit()
            flash(f"Lot « {lot.nom} » créé.", "success")
        return redirect(url_for("caille.lots"))

    filtre_statut = request.args.get("statut", "actif")
    query = Lot.query
    if filtre_statut != "tous":
        query = query.filter_by(statut=filtre_statut)
    liste_lots = query.order_by(Lot.date_mise_en_place.desc()).all()
    especes = Espece.query.order_by(Espece.nom).all()
    return render_template("lots.html", lots=liste_lots, filtre_statut=filtre_statut, especes=especes)


@caille_bp.route("/lots/<int:lot_id>/modifier", methods=["POST"])
def modifier_lot(lot_id):
    lot = Lot.query.get_or_404(lot_id)
    lot.nom = request.form.get("nom", lot.nom).strip()
    lot.espece_id = _parse_int(request.form.get("espece_id")) or None
    lot.type_lot = request.form.get("type_lot", lot.type_lot)
    lot.date_mise_en_place = _parse_date(request.form.get("date_mise_en_place"), lot.date_mise_en_place)
    lot.effectif_initial = _parse_int(request.form.get("effectif_initial"), lot.effectif_initial)
    lot.notes = request.form.get("notes")
    db.session.commit()
    flash(f"Lot « {lot.nom} » mis à jour.", "success")
    return redirect(url_for("caille.lots"))


@caille_bp.route("/lots/<int:lot_id>/archiver", methods=["POST"])
def archiver_lot(lot_id):
    lot = Lot.query.get_or_404(lot_id)
    lot.statut = "archive"
    lot.date_reforme = date.today()
    db.session.commit()
    flash(f"Lot « {lot.nom} » archivé (réformé).", "info")
    return redirect(url_for("caille.lots"))


@caille_bp.route("/lots/<int:lot_id>/reactiver", methods=["POST"])
def reactiver_lot(lot_id):
    lot = Lot.query.get_or_404(lot_id)
    lot.statut = "actif"
    lot.date_reforme = None
    db.session.commit()
    flash(f"Lot « {lot.nom} » réactivé.", "info")
    return redirect(url_for("caille.lots"))


@caille_bp.route("/lots/<int:lot_id>")
def detail_lot(lot_id):
    lot = Lot.query.get_or_404(lot_id)
    pontes = lot.pontes.order_by(SuiviPonte.date_jour.desc()).limit(30).all()
    mortalites = lot.mortalites.order_by(SuiviMortalite.date_jour.desc()).limit(30).all()
    naissances = lot.naissances.order_by(Naissance.date_jour.desc()).limit(30).all()
    soins = SoinSante.query.filter_by(lot_id=lot.id).order_by(SoinSante.date_soin.desc()).limit(20).all()
    pesees = PeseeCroissance.query.filter_by(lot_id=lot.id).order_by(PeseeCroissance.date_pesee.desc()).limit(20).all()
    return render_template("lot_detail.html", lot=lot, pontes=pontes, mortalites=mortalites,
                            naissances=naissances, soins=soins, pesees=pesees, types_soin=TYPES_SOIN)


# ---------------------------------------------------------------------------
# ESPÈCES / TYPES D'ÉLEVAGE (Caille, Poule, Lapin, ...)
# ---------------------------------------------------------------------------
@caille_bp.route("/especes", methods=["GET", "POST"])
def especes():
    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        if not nom:
            flash("Le nom de l'espèce est obligatoire.", "danger")
        elif Espece.query.filter_by(nom=nom).first():
            flash(f"« {nom} » existe déjà.", "danger")
        else:
            db.session.add(Espece(
                nom=nom, categorie_id=_parse_int(request.form.get("categorie_id")) or None,
                description=request.form.get("description"),
            ))
            db.session.commit()
            flash(f"Espèce « {nom} » ajoutée. Vous pouvez maintenant créer des lots de ce type.", "success")
        return redirect(url_for("caille.especes"))

    liste = Espece.query.order_by(Espece.nom).all()
    categories = CategorieElevage.query.order_by(CategorieElevage.nom).all()
    return render_template("especes.html", especes=liste, categories=categories)


@caille_bp.route("/especes/<int:espece_id>")
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

    return render_template(
        "espece_detail.html", espece=espece, lots=lots_espece, pond_des_oeufs=pond_des_oeufs,
        effectif_total=effectif_total, mortalite_adultes=mortalite_adultes, mortalite_jeunes=mortalite_jeunes,
        naissances_total=naissances_total, oeufs_pondus_total=oeufs_pondus_total,
        revenu_total=revenu_total, cout_provende_total=cout_provende_total,
        depenses_total=depenses_total, marge_total=marge_total,
        soins_recents=soins_recents, pesees_recentes=pesees_recentes, types_soin=TYPES_SOIN,
    )


# ---------------------------------------------------------------------------
# CATÉGORIES D'ÉLEVAGE (Aviculture, Cuniculture, ...)
# ---------------------------------------------------------------------------
@caille_bp.route("/categories-elevage", methods=["GET", "POST"])
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
        return redirect(url_for("caille.categories_elevage"))

    liste = CategorieElevage.query.order_by(CategorieElevage.nom).all()
    return render_template("categories_elevage.html", categories=liste)


@caille_bp.route("/categories-elevage/<int:categorie_id>/oeufs", methods=["POST"])
def basculer_produit_des_oeufs(categorie_id):
    c = CategorieElevage.query.get_or_404(categorie_id)
    c.produit_des_oeufs = not c.produit_des_oeufs
    db.session.commit()
    flash(f"« {c.nom} » {'produit' if c.produit_des_oeufs else 'ne produit plus'} des œufs (page Ponte).", "info")
    return redirect(url_for("caille.categories_elevage"))


# ---------------------------------------------------------------------------
# PERSONNEL
# ---------------------------------------------------------------------------
@caille_bp.route("/personnel", methods=["GET", "POST"])
def personnel():
    if request.method == "POST":
        e = Employe(
            nom=request.form.get("nom", "").strip(),
            role=request.form.get("role"),
            telephone=request.form.get("telephone"),
            date_embauche=_parse_date(request.form.get("date_embauche"), None) if request.form.get("date_embauche") else None,
            notes=request.form.get("notes"),
        )
        if not e.nom:
            flash("Le nom de l'employé est obligatoire.", "danger")
        else:
            db.session.add(e)
            db.session.commit()
            flash(f"Employé « {e.nom} » ajouté.", "success")
        return redirect(url_for("caille.personnel"))

    liste = Employe.query.order_by(Employe.statut.desc(), Employe.nom).all()
    return render_template("personnel.html", employes=liste)


@caille_bp.route("/personnel/<int:employe_id>/statut", methods=["POST"])
def changer_statut_employe(employe_id):
    e = Employe.query.get_or_404(employe_id)
    e.statut = "inactif" if e.statut == "actif" else "actif"
    db.session.commit()
    flash(f"{e.nom} marqué « {e.statut} ».", "info")
    return redirect(url_for("caille.personnel"))


# ---------------------------------------------------------------------------
# SUIVI SANITAIRE (vaccinations, traitements, maladies)
# ---------------------------------------------------------------------------
TYPES_SOIN = {
    "vaccination": "Vaccination",
    "traitement": "Traitement",
    "maladie": "Maladie / diagnostic",
    "visite_veterinaire": "Visite vétérinaire",
}


@caille_bp.route("/sante", methods=["GET", "POST"])
def sante():
    if request.method == "POST":
        s = SoinSante(
            lot_id=_parse_int(request.form.get("lot_id")),
            date_soin=_parse_date(request.form.get("date_soin")),
            type_soin=request.form.get("type_soin", "vaccination"),
            produit=request.form.get("produit"),
            employe_id=_parse_int(request.form.get("employe_id")) or None,
            notes=request.form.get("notes"),
        )
        db.session.add(s)
        db.session.commit()
        flash("Soin de santé enregistré.", "success")
        return redirect(url_for("caille.sante"))

    date_debut = _parse_date(request.args.get("debut"), date.today() - timedelta(days=89))
    date_fin = _parse_date(request.args.get("fin"), date.today())
    entrees = SoinSante.query.filter(SoinSante.date_soin.between(date_debut, date_fin)) \
        .order_by(SoinSante.date_soin.desc()).all()

    lots_tous = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    employes_actifs = Employe.query.filter_by(statut="actif").order_by(Employe.nom).all()
    return render_template(
        "sante.html", entrees=entrees, lots=lots_tous, employes=employes_actifs,
        types_soin=TYPES_SOIN, date_debut=date_debut, date_fin=date_fin,
    )


@caille_bp.route("/sante/<int:soin_id>/supprimer", methods=["POST"])
def supprimer_soin(soin_id):
    s = SoinSante.query.get_or_404(soin_id)
    db.session.delete(s)
    db.session.commit()
    flash("Soin supprimé.", "info")
    return redirect(url_for("caille.sante"))


# ---------------------------------------------------------------------------
# CLIENTS
# ---------------------------------------------------------------------------
@caille_bp.route("/clients", methods=["GET", "POST"])
def clients():
    if request.method == "POST":
        c = Client(
            nom=request.form.get("nom", "").strip(),
            telephone=request.form.get("telephone"),
            adresse=request.form.get("adresse"),
            notes=request.form.get("notes"),
        )
        if not c.nom:
            flash("Le nom du client est obligatoire.", "danger")
        else:
            db.session.add(c)
            db.session.commit()
            flash(f"Client « {c.nom} » ajouté.", "success")
        return redirect(url_for("caille.clients"))

    liste = Client.query.order_by(Client.nom).all()
    return render_template("clients.html", clients=liste)


# ---------------------------------------------------------------------------
# VENTES (carnet de ventes général — cailles vivantes, viande, sous-produits...)
# ---------------------------------------------------------------------------
@caille_bp.route("/ventes", methods=["GET", "POST"])
def ventes():
    if request.method == "POST":
        v = Vente(
            date_vente=_parse_date(request.form.get("date_vente")),
            client_id=_parse_int(request.form.get("client_id")) or None,
            lot_id=_parse_int(request.form.get("lot_id")) or None,
            produit=request.form.get("produit", "").strip(),
            quantite=_parse_float(request.form.get("quantite")),
            unite=request.form.get("unite", "unité"),
            prix_unitaire=_parse_float(request.form.get("prix_unitaire")),
            notes=request.form.get("notes"),
        )
        if not v.produit:
            flash("Le produit vendu est obligatoire.", "danger")
        else:
            db.session.add(v)
            db.session.commit()
            flash(f"Vente de « {v.produit} » enregistrée ({v.montant_total} F).", "success")
        return redirect(url_for("caille.ventes"))

    date_debut = _parse_date(request.args.get("debut"), date.today() - timedelta(days=29))
    date_fin = _parse_date(request.args.get("fin"), date.today())
    entrees = Vente.query.filter(Vente.date_vente.between(date_debut, date_fin)) \
        .order_by(Vente.date_vente.desc()).all()
    total = round(sum(v.montant_total for v in entrees), 2)

    clients_tous = Client.query.order_by(Client.nom).all()
    lots_tous = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    return render_template(
        "ventes.html", entrees=entrees, clients=clients_tous, lots=lots_tous,
        total=total, date_debut=date_debut, date_fin=date_fin,
    )


@caille_bp.route("/ventes/<int:vente_id>/supprimer", methods=["POST"])
def supprimer_vente(vente_id):
    v = Vente.query.get_or_404(vente_id)
    db.session.delete(v)
    db.session.commit()
    flash("Vente supprimée.", "info")
    return redirect(url_for("caille.ventes"))


# ---------------------------------------------------------------------------
# CROISSANCE / POIDS (lots destinés à la viande)
# ---------------------------------------------------------------------------
@caille_bp.route("/croissance", methods=["GET", "POST"])
def croissance():
    if request.method == "POST":
        p = PeseeCroissance(
            lot_id=_parse_int(request.form.get("lot_id")),
            date_pesee=_parse_date(request.form.get("date_pesee")),
            poids_moyen_g=_parse_float(request.form.get("poids_moyen_g")),
            nombre_pese=_parse_int(request.form.get("nombre_pese")) or None,
            notes=request.form.get("notes"),
        )
        db.session.add(p)
        db.session.commit()
        flash("Pesée enregistrée.", "success")
        return redirect(url_for("caille.croissance"))

    lot_filtre = request.args.get("lot_id")
    query = PeseeCroissance.query
    if lot_filtre:
        query = query.filter_by(lot_id=_parse_int(lot_filtre))
    entrees = query.order_by(PeseeCroissance.date_pesee.desc()).limit(100).all()
    lots_tous = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    return render_template("croissance.html", entrees=entrees, lots=lots_tous, lot_filtre=lot_filtre)


@caille_bp.route("/croissance/<int:pesee_id>/supprimer", methods=["POST"])
def supprimer_pesee(pesee_id):
    p = PeseeCroissance.query.get_or_404(pesee_id)
    db.session.delete(p)
    db.session.commit()
    flash("Pesée supprimée.", "info")
    return redirect(url_for("caille.croissance"))


@caille_bp.route("/api/stats/croissance")
def api_stats_croissance():
    lot_id = request.args.get("lot_id")
    query = PeseeCroissance.query
    if lot_id:
        query = query.filter_by(lot_id=_parse_int(lot_id))
    rows = query.order_by(PeseeCroissance.date_pesee).all()
    return jsonify({
        "labels": [r.date_pesee.strftime("%d/%m/%Y") for r in rows],
        "poids": [r.poids_moyen_g for r in rows],
    })


# ---------------------------------------------------------------------------
# PONTE / VENTE D'ŒUFS
# ---------------------------------------------------------------------------
@caille_bp.route("/ponte", methods=["GET", "POST"])
def ponte():
    lots_pondeurs = Lot.query.join(Espece, Lot.espece_id == Espece.id) \
        .join(CategorieElevage, Espece.categorie_id == CategorieElevage.id) \
        .filter(Lot.statut != "archive", CategorieElevage.produit_des_oeufs.is_(True)) \
        .order_by(Lot.nom).all()
    ids_lots_pondeurs = {l.id for l in lots_pondeurs}

    if request.method == "POST":
        lot_id = _parse_int(request.form.get("lot_id"))
        if lot_id not in ids_lots_pondeurs:
            flash("Ce lot n'appartient pas à une espèce productrice d'œufs (voir Catégories d'élevage).", "danger")
            return redirect(url_for("caille.ponte"))
        date_jour = _parse_date(request.form.get("date_jour"))
        entree = SuiviPonte.query.filter_by(lot_id=lot_id, date_jour=date_jour).first()
        if entree is None:
            entree = SuiviPonte(lot_id=lot_id, date_jour=date_jour)
            db.session.add(entree)
        entree.oeufs_pondus = _parse_int(request.form.get("oeufs_pondus"))
        entree.oeufs_vendus = _parse_int(request.form.get("oeufs_vendus"))
        entree.prix_unitaire_vente = _parse_float(request.form.get("prix_unitaire_vente"))
        entree.plateaux_vendus = _parse_int(request.form.get("plateaux_vendus"))
        entree.prix_plateau_vente = _parse_float(request.form.get("prix_plateau_vente"))
        entree.oeufs_casses = _parse_int(request.form.get("oeufs_casses"))
        entree.oeufs_autoconsommes = _parse_int(request.form.get("oeufs_autoconsommes"))
        entree.notes = request.form.get("notes")
        db.session.commit()
        flash("Entrée de ponte enregistrée.", "success")
        return redirect(url_for("caille.ponte"))

    date_debut = _parse_date(request.args.get("debut"), date.today() - timedelta(days=13))
    date_fin = _parse_date(request.args.get("fin"), date.today())
    query = SuiviPonte.query.filter(SuiviPonte.date_jour.between(date_debut, date_fin))
    lot_filtre = request.args.get("lot_id")
    if lot_filtre:
        query = query.filter_by(lot_id=_parse_int(lot_filtre))
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

    return render_template(
        "ponte.html", entrees=entrees, lots=lots_pondeurs, totaux=totaux,
        date_debut=date_debut, date_fin=date_fin, lot_filtre=lot_filtre,
        stock_oeufs=stock_oeufs_actuel(), taille_plateau=SuiviPonte.TAILLE_PLATEAU,
    )


@caille_bp.route("/ponte/<int:entree_id>/supprimer", methods=["POST"])
def supprimer_ponte(entree_id):
    entree = SuiviPonte.query.get_or_404(entree_id)
    db.session.delete(entree)
    db.session.commit()
    flash("Entrée de ponte supprimée.", "info")
    return redirect(url_for("caille.ponte"))


# ---------------------------------------------------------------------------
# MORTALITÉ
# ---------------------------------------------------------------------------
@caille_bp.route("/mortalite", methods=["GET", "POST"])
def mortalite():
    if request.method == "POST":
        lot_id = _parse_int(request.form.get("lot_id"))
        date_jour = _parse_date(request.form.get("date_jour"))
        entree = SuiviMortalite.query.filter_by(lot_id=lot_id, date_jour=date_jour).first()
        if entree is None:
            entree = SuiviMortalite(lot_id=lot_id, date_jour=date_jour)
            db.session.add(entree)
        entree.cailles_mortes = _parse_int(request.form.get("cailles_mortes"))
        entree.cailletons_morts = _parse_int(request.form.get("cailletons_morts"))
        entree.cause = request.form.get("cause")
        entree.notes = request.form.get("notes")
        db.session.commit()
        flash("Mortalité du jour enregistrée.", "success")
        return redirect(url_for("caille.mortalite"))

    date_debut = _parse_date(request.args.get("debut"), date.today() - timedelta(days=13))
    date_fin = _parse_date(request.args.get("fin"), date.today())
    entrees = SuiviMortalite.query.filter(
        SuiviMortalite.date_jour.between(date_debut, date_fin)
    ).order_by(SuiviMortalite.date_jour.desc()).all()

    totaux = {
        "cailles": sum(e.cailles_mortes for e in entrees),
        "cailletons": sum(e.cailletons_morts for e in entrees),
    }
    lots_actifs = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    return render_template(
        "mortalite.html", entrees=entrees, lots=lots_actifs, totaux=totaux,
        date_debut=date_debut, date_fin=date_fin,
    )


# ---------------------------------------------------------------------------
# NAISSANCES / CAILLETONS
# ---------------------------------------------------------------------------
@caille_bp.route("/naissances", methods=["GET", "POST"])
def naissances():
    if request.method == "POST":
        entree = Naissance(
            lot_id=_parse_int(request.form.get("lot_id")),
            date_jour=_parse_date(request.form.get("date_jour")),
            nombre_cailletons=_parse_int(request.form.get("nombre_cailletons")),
            origine=request.form.get("origine", "eclosion"),
            notes=request.form.get("notes"),
        )
        db.session.add(entree)
        db.session.commit()
        flash("Naissance enregistrée.", "success")
        return redirect(url_for("caille.naissances"))

    entrees = Naissance.query.order_by(Naissance.date_jour.desc()).limit(60).all()
    lots_actifs = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    return render_template("naissances.html", entrees=entrees, lots=lots_actifs)


# ---------------------------------------------------------------------------
# PROVENDE : TYPES
# ---------------------------------------------------------------------------
@caille_bp.route("/provende/types", methods=["GET", "POST"])
def types_provende():
    if request.method == "POST":
        t = TypeProvende(
            nom=request.form.get("nom", "").strip(),
            description=request.form.get("description"),
            seuil_alerte_kg=_parse_float(request.form.get("seuil_alerte_kg"), 20),
        )
        if not t.nom:
            flash("Le nom du type de provende est obligatoire.", "danger")
        else:
            db.session.add(t)
            db.session.commit()
            flash(f"Type de provende « {t.nom} » ajouté.", "success")
        return redirect(url_for("caille.types_provende"))

    types = TypeProvende.query.order_by(TypeProvende.nom).all()
    return render_template("provende_types.html", types=types)


@caille_bp.route("/provende/types/<int:type_id>/desactiver", methods=["POST"])
def desactiver_type_provende(type_id):
    t = TypeProvende.query.get_or_404(type_id)
    t.actif = not t.actif
    db.session.commit()
    return redirect(url_for("caille.types_provende"))


# ---------------------------------------------------------------------------
# PROVENDE : ACHATS (réapprovisionnement)
# ---------------------------------------------------------------------------
@caille_bp.route("/provende/achats", methods=["GET", "POST"])
def achats_provende():
    if request.method == "POST":
        achat = AchatProvende(
            date_achat=_parse_date(request.form.get("date_achat")),
            type_provende_id=_parse_int(request.form.get("type_provende_id")),
            fournisseur_id=_parse_int(request.form.get("fournisseur_id")) or None,
            quantite_kg=_parse_float(request.form.get("quantite_kg")),
            prix_total=_parse_float(request.form.get("prix_total")),
            notes=request.form.get("notes"),
        )
        db.session.add(achat)
        db.session.commit()
        flash(f"Achat de {achat.quantite_kg} kg enregistré.", "success")
        return redirect(url_for("caille.achats_provende"))

    date_debut = _parse_date(request.args.get("debut"), date.today() - timedelta(days=29))
    date_fin = _parse_date(request.args.get("fin"), date.today())
    achats = AchatProvende.query.filter(
        AchatProvende.date_achat.between(date_debut, date_fin)
    ).order_by(AchatProvende.date_achat.desc()).all()

    totaux = {
        "kg": round(sum(a.quantite_kg for a in achats), 2),
        "cout": round(sum(a.prix_total or 0 for a in achats), 2),
    }
    types = TypeProvende.query.order_by(TypeProvende.nom).all()
    fournisseurs = Fournisseur.query.order_by(Fournisseur.nom).all()
    return render_template(
        "provende_achats.html", achats=achats, types=types, fournisseurs=fournisseurs,
        totaux=totaux, date_debut=date_debut, date_fin=date_fin,
    )


# ---------------------------------------------------------------------------
# PROVENDE : CONSOMMATION
# ---------------------------------------------------------------------------
@caille_bp.route("/provende/consommation", methods=["GET", "POST"])
def consommation_provende():
    if request.method == "POST":
        c = ConsommationProvende(
            date_jour=_parse_date(request.form.get("date_jour")),
            lot_id=_parse_int(request.form.get("lot_id")) or None,
            type_provende_id=_parse_int(request.form.get("type_provende_id")),
            quantite_kg=_parse_float(request.form.get("quantite_kg")),
            notes=request.form.get("notes"),
        )
        db.session.add(c)
        db.session.commit()
        flash("Consommation enregistrée.", "success")
        return redirect(url_for("caille.consommation_provende"))

    date_debut = _parse_date(request.args.get("debut"), date.today() - timedelta(days=13))
    date_fin = _parse_date(request.args.get("fin"), date.today())
    consos = ConsommationProvende.query.filter(
        ConsommationProvende.date_jour.between(date_debut, date_fin)
    ).order_by(ConsommationProvende.date_jour.desc()).all()

    types = TypeProvende.query.order_by(TypeProvende.nom).all()
    lots_actifs = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    total_kg = round(sum(c.quantite_kg for c in consos), 2)
    return render_template(
        "provende_consommation.html", consos=consos, types=types, lots=lots_actifs,
        total_kg=total_kg, date_debut=date_debut, date_fin=date_fin,
    )


# ---------------------------------------------------------------------------
# FOURNISSEURS
# ---------------------------------------------------------------------------
@caille_bp.route("/fournisseurs", methods=["GET", "POST"])
def fournisseurs():
    if request.method == "POST":
        f = Fournisseur(
            nom=request.form.get("nom", "").strip(),
            contact=request.form.get("contact"),
            adresse=request.form.get("adresse"),
            notes=request.form.get("notes"),
        )
        if not f.nom:
            flash("Le nom du fournisseur est obligatoire.", "danger")
        else:
            db.session.add(f)
            db.session.commit()
            flash(f"Fournisseur « {f.nom} » ajouté.", "success")
        return redirect(url_for("caille.fournisseurs"))

    liste = Fournisseur.query.order_by(Fournisseur.nom).all()
    return render_template("fournisseurs.html", fournisseurs=liste)


# ---------------------------------------------------------------------------
# DÉPENSES DIVERSES (vaccination, médicament, transport, matériel...)
# ---------------------------------------------------------------------------
CATEGORIES_DEPENSE_SUGGESTIONS = [
    "Vaccination", "Médicament", "Alimentation complémentaire",
    "Transport", "Matériel", "Main d'œuvre", "Entretien", "Autre",
]


@caille_bp.route("/depenses", methods=["GET", "POST"])
def depenses():
    if request.method == "POST":
        categorie = request.form.get("categorie", "").strip()
        d = Depense(
            date_depense=_parse_date(request.form.get("date_depense")),
            categorie=categorie,
            montant=_parse_float(request.form.get("montant")),
            lot_id=_parse_int(request.form.get("lot_id")) or None,
            notes=request.form.get("notes"),
        )
        if not categorie:
            flash("La catégorie de la dépense est obligatoire (ex: Vaccination, Transport...).", "danger")
        else:
            db.session.add(d)
            db.session.commit()
            flash(f"Dépense « {categorie} » de {d.montant} F enregistrée.", "success")
        return redirect(url_for("caille.depenses"))

    date_debut = _parse_date(request.args.get("debut"), date.today() - timedelta(days=29))
    date_fin = _parse_date(request.args.get("fin"), date.today())
    entrees = Depense.query.filter(Depense.date_depense.between(date_debut, date_fin)) \
        .order_by(Depense.date_depense.desc()).all()
    total = round(sum(d.montant for d in entrees), 2)

    lots_tous = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    return render_template(
        "depenses.html", entrees=entrees, lots=lots_tous, total=total,
        date_debut=date_debut, date_fin=date_fin,
        suggestions=CATEGORIES_DEPENSE_SUGGESTIONS,
    )


@caille_bp.route("/depenses/<int:depense_id>/supprimer", methods=["POST"])
def supprimer_depense(depense_id):
    d = Depense.query.get_or_404(depense_id)
    db.session.delete(d)
    db.session.commit()
    flash("Dépense supprimée.", "info")
    return redirect(url_for("caille.depenses"))


# ---------------------------------------------------------------------------
# CAHIER DE CHARGES (tâches / protocoles)
# ---------------------------------------------------------------------------
@caille_bp.route("/taches", methods=["GET", "POST"])
def taches():
    if request.method == "POST":
        t = Tache(
            titre=request.form.get("titre", "").strip(),
            description=request.form.get("description"),
            categorie=request.form.get("categorie", "general"),
            date_prevue=_parse_date(request.form.get("date_prevue"), None) if request.form.get("date_prevue") else None,
            recurrence=request.form.get("recurrence", "aucune"),
            lot_id=_parse_int(request.form.get("lot_id")) or None,
            employe_id=_parse_int(request.form.get("employe_id")) or None,
            notes=request.form.get("notes"),
        )
        if not t.titre:
            flash("Le titre de la tâche est obligatoire.", "danger")
        else:
            db.session.add(t)
            db.session.commit()
            flash(f"Tâche « {t.titre} » ajoutée au cahier de charges.", "success")
        return redirect(url_for("caille.taches"))

    filtre_statut = request.args.get("statut", "tous")
    query = Tache.query
    if filtre_statut != "tous":
        query = query.filter_by(statut=filtre_statut)
    liste = query.order_by(Tache.date_prevue.asc().nullslast()).all()
    lots_actifs = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    employes_actifs = Employe.query.filter_by(statut="actif").order_by(Employe.nom).all()
    return render_template("taches.html", taches=liste, lots=lots_actifs, employes=employes_actifs, filtre_statut=filtre_statut)


RECURRENCE_DELTA = {
    "quotidien": timedelta(days=1),
    "hebdo": timedelta(weeks=1),
    "mensuel": timedelta(days=30),
}


@caille_bp.route("/taches/<int:tache_id>/statut", methods=["POST"])
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
    return redirect(url_for("caille.taches"))


# ---------------------------------------------------------------------------
# ARCHIVE
# ---------------------------------------------------------------------------
@caille_bp.route("/archive")
def archive():
    lots_archives = Lot.query.filter_by(statut="archive").order_by(Lot.date_reforme.desc()).all()
    return render_template("archive.html", lots=lots_archives)


# ---------------------------------------------------------------------------
# STATISTIQUES (graphiques)
# ---------------------------------------------------------------------------
@caille_bp.route("/statistiques")
def statistiques():
    lots_actifs = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    date_debut = date.today() - timedelta(days=29)
    date_fin = date.today()
    return render_template("statistiques.html", lots=lots_actifs, date_debut=date_debut, date_fin=date_fin)


@caille_bp.route("/api/stats/ponte")
def api_stats_ponte():
    date_debut = _parse_date(request.args.get("debut"), date.today() - timedelta(days=29))
    date_fin = _parse_date(request.args.get("fin"), date.today())
    lot_id = request.args.get("lot_id")

    query = db.session.query(
        SuiviPonte.date_jour,
        db.func.sum(SuiviPonte.oeufs_pondus),
        db.func.sum(SuiviPonte.oeufs_vendus),
    ).filter(SuiviPonte.date_jour.between(date_debut, date_fin))
    if lot_id:
        query = query.filter(SuiviPonte.lot_id == _parse_int(lot_id))
    rows = query.group_by(SuiviPonte.date_jour).order_by(SuiviPonte.date_jour).all()

    return jsonify({
        "labels": [r[0].strftime("%d/%m") for r in rows],
        "pondus": [int(r[1] or 0) for r in rows],
        "vendus": [int(r[2] or 0) for r in rows],
    })


@caille_bp.route("/api/stats/mortalite")
def api_stats_mortalite():
    date_debut = _parse_date(request.args.get("debut"), date.today() - timedelta(days=29))
    date_fin = _parse_date(request.args.get("fin"), date.today())
    lot_id = request.args.get("lot_id")

    query = db.session.query(
        SuiviMortalite.date_jour,
        db.func.sum(SuiviMortalite.cailles_mortes),
        db.func.sum(SuiviMortalite.cailletons_morts),
    ).filter(SuiviMortalite.date_jour.between(date_debut, date_fin))
    if lot_id:
        query = query.filter(SuiviMortalite.lot_id == _parse_int(lot_id))
    rows = query.group_by(SuiviMortalite.date_jour).order_by(SuiviMortalite.date_jour).all()

    return jsonify({
        "labels": [r[0].strftime("%d/%m") for r in rows],
        "cailles": [int(r[1] or 0) for r in rows],
        "cailletons": [int(r[2] or 0) for r in rows],
    })


# ---------------------------------------------------------------------------
# RAPPORTS (PDF + Excel)
# ---------------------------------------------------------------------------
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@caille_bp.route("/rapports")
def rapports():
    lots_tous = Lot.query.order_by(Lot.nom).all()
    date_debut = date.today() - timedelta(days=29)
    date_fin = date.today()
    return render_template("rapports.html", lots=lots_tous, date_debut=date_debut, date_fin=date_fin)


# ---- Fonctions internes de préparation des données (partagées PDF / Excel) ----
def _donnees_ponte(debut_param, fin_param):
    date_debut = _parse_date(debut_param, date.today() - timedelta(days=29))
    date_fin = _parse_date(fin_param, date.today())
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
    date_debut = _parse_date(debut_param, date.today() - timedelta(days=29))
    date_fin = _parse_date(fin_param, date.today())
    entrees = SuiviMortalite.query.filter(SuiviMortalite.date_jour.between(date_debut, date_fin)) \
        .order_by(SuiviMortalite.date_jour).all()
    totaux = {
        "cailles": sum(e.cailles_mortes for e in entrees),
        "cailletons": sum(e.cailletons_morts for e in entrees),
    }
    return entrees, date_debut, date_fin, totaux


def _donnees_achats(debut_param, fin_param):
    date_debut = _parse_date(debut_param, date.today() - timedelta(days=29))
    date_fin = _parse_date(fin_param, date.today())
    achats = AchatProvende.query.filter(AchatProvende.date_achat.between(date_debut, date_fin)) \
        .order_by(AchatProvende.date_achat).all()
    totaux = {
        "kg": round(sum(a.quantite_kg for a in achats), 2),
        "cout": round(sum(a.prix_total or 0 for a in achats), 2),
    }
    return achats, date_debut, date_fin, totaux


def _donnees_naissances(debut_param, fin_param):
    date_debut = _parse_date(debut_param, date.today() - timedelta(days=29))
    date_fin = _parse_date(fin_param, date.today())
    entrees = Naissance.query.filter(Naissance.date_jour.between(date_debut, date_fin)) \
        .order_by(Naissance.date_jour).all()
    total = sum(e.nombre_cailletons for e in entrees)
    return entrees, date_debut, date_fin, total


def _donnees_consommation(debut_param, fin_param):
    date_debut = _parse_date(debut_param, date.today() - timedelta(days=29))
    date_fin = _parse_date(fin_param, date.today())
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
    date_debut = _parse_date(debut_param, date.today() - timedelta(days=29))
    date_fin = _parse_date(fin_param, date.today())
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
        date_debut = _parse_date(debut_param, date(1900, 1, 1))
        date_fin = _parse_date(fin_param, date.today())
        pontes_q = pontes_q.filter(SuiviPonte.date_jour.between(date_debut, date_fin))
        mortalites_q = mortalites_q.filter(SuiviMortalite.date_jour.between(date_debut, date_fin))
        naissances_q = naissances_q.filter(Naissance.date_jour.between(date_debut, date_fin))

    return lot, pontes_q.all(), mortalites_q.all(), naissances_q.all()


# ---- Ponte ----
@caille_bp.route("/rapports/ponte.pdf")
def rapport_ponte_pdf():
    entrees, date_debut, date_fin, totaux = _donnees_ponte(request.args.get("debut"), request.args.get("fin"))
    buf = reports.rapport_ponte(entrees, date_debut, date_fin, totaux)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"rapport_ponte_{date_debut}_{date_fin}.pdf")


@caille_bp.route("/rapports/ponte.xlsx")
def rapport_ponte_excel():
    entrees, date_debut, date_fin, totaux = _donnees_ponte(request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_ponte(entrees, totaux)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"rapport_ponte_{date_debut}_{date_fin}.xlsx")


# ---- Mortalité ----
@caille_bp.route("/rapports/mortalite.pdf")
def rapport_mortalite_pdf():
    entrees, date_debut, date_fin, totaux = _donnees_mortalite(request.args.get("debut"), request.args.get("fin"))
    buf = reports.rapport_mortalite(entrees, date_debut, date_fin, totaux)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"rapport_mortalite_{date_debut}_{date_fin}.pdf")


@caille_bp.route("/rapports/mortalite.xlsx")
def rapport_mortalite_excel():
    entrees, date_debut, date_fin, totaux = _donnees_mortalite(request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_mortalite(entrees, totaux)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"rapport_mortalite_{date_debut}_{date_fin}.xlsx")


# ---- Achats de provende ----
@caille_bp.route("/rapports/achats.pdf")
def rapport_achats_pdf():
    achats, date_debut, date_fin, totaux = _donnees_achats(request.args.get("debut"), request.args.get("fin"))
    buf = reports.rapport_achats(achats, date_debut, date_fin, totaux)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"rapport_achats_provende_{date_debut}_{date_fin}.pdf")


@caille_bp.route("/rapports/achats.xlsx")
def rapport_achats_excel():
    achats, date_debut, date_fin, totaux = _donnees_achats(request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_achats(achats, totaux)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"rapport_achats_provende_{date_debut}_{date_fin}.xlsx")


# ---- Fiche d'un lot ----
@caille_bp.route("/rapports/lot/<int:lot_id>.pdf")
def rapport_lot_pdf(lot_id):
    lot, pontes, mortalites, naissances = _donnees_lot(lot_id, request.args.get("debut"), request.args.get("fin"))
    buf = reports.fiche_lot(lot, pontes, mortalites, naissances)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"fiche_{lot.nom}.pdf")


@caille_bp.route("/rapports/lot/<int:lot_id>.xlsx")
def rapport_lot_excel(lot_id):
    lot, pontes, mortalites, naissances = _donnees_lot(lot_id, request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_lot(lot, pontes, mortalites, naissances)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"fiche_{lot.nom}.xlsx")


# ---- Naissances ----
@caille_bp.route("/rapports/naissances.pdf")
def rapport_naissances_pdf():
    entrees, date_debut, date_fin, total = _donnees_naissances(request.args.get("debut"), request.args.get("fin"))
    buf = reports.rapport_naissances(entrees, date_debut, date_fin, total)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"rapport_naissances_{date_debut}_{date_fin}.pdf")


@caille_bp.route("/rapports/naissances.xlsx")
def rapport_naissances_excel():
    entrees, date_debut, date_fin, total = _donnees_naissances(request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_naissances(entrees, total)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"rapport_naissances_{date_debut}_{date_fin}.xlsx")


# ---- Consommation de provende ----
@caille_bp.route("/rapports/consommation.pdf")
def rapport_consommation_pdf():
    entrees, date_debut, date_fin, total_kg = _donnees_consommation(request.args.get("debut"), request.args.get("fin"))
    buf = reports.rapport_consommation(entrees, date_debut, date_fin, total_kg)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"rapport_consommation_{date_debut}_{date_fin}.pdf")


@caille_bp.route("/rapports/consommation.xlsx")
def rapport_consommation_excel():
    entrees, date_debut, date_fin, total_kg = _donnees_consommation(request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_consommation(entrees, total_kg)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"rapport_consommation_{date_debut}_{date_fin}.xlsx")


# ---- Cahier de charges ----
@caille_bp.route("/rapports/taches.pdf")
def rapport_taches_pdf():
    filtre_statut = request.args.get("statut", "tous")
    taches_liste = _donnees_taches(filtre_statut)
    buf = reports.rapport_taches(taches_liste, filtre_statut)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"cahier_de_charges_{filtre_statut}.pdf")


@caille_bp.route("/rapports/taches.xlsx")
def rapport_taches_excel():
    filtre_statut = request.args.get("statut", "tous")
    taches_liste = _donnees_taches(filtre_statut)
    buf = excel_reports.excel_taches(taches_liste)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"cahier_de_charges_{filtre_statut}.xlsx")


# ---- Fournisseurs ----
@caille_bp.route("/rapports/fournisseurs.pdf")
def rapport_fournisseurs_pdf():
    liste = Fournisseur.query.order_by(Fournisseur.nom).all()
    buf = reports.rapport_fournisseurs(liste)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name="fournisseurs.pdf")


@caille_bp.route("/rapports/fournisseurs.xlsx")
def rapport_fournisseurs_excel():
    liste = Fournisseur.query.order_by(Fournisseur.nom).all()
    buf = excel_reports.excel_fournisseurs(liste)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name="fournisseurs.xlsx")


# ---- Dépenses diverses ----
@caille_bp.route("/rapports/depenses.pdf")
def rapport_depenses_pdf():
    entrees, date_debut, date_fin, total = _donnees_depenses(request.args.get("debut"), request.args.get("fin"))
    buf = reports.rapport_depenses(entrees, date_debut, date_fin, total)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"rapport_depenses_{date_debut}_{date_fin}.pdf")


@caille_bp.route("/rapports/depenses.xlsx")
def rapport_depenses_excel():
    entrees, date_debut, date_fin, total = _donnees_depenses(request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_depenses(entrees, total)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"rapport_depenses_{date_debut}_{date_fin}.xlsx")


# ---- Personnel ----
@caille_bp.route("/rapports/personnel.pdf")
def rapport_personnel_pdf():
    liste = Employe.query.order_by(Employe.statut.desc(), Employe.nom).all()
    buf = reports.rapport_personnel(liste)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="personnel.pdf")


@caille_bp.route("/rapports/personnel.xlsx")
def rapport_personnel_excel():
    liste = Employe.query.order_by(Employe.statut.desc(), Employe.nom).all()
    buf = excel_reports.excel_personnel(liste)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True, download_name="personnel.xlsx")


# ---- Santé ----
def _donnees_sante(debut_param, fin_param):
    date_debut = _parse_date(debut_param, date.today() - timedelta(days=89))
    date_fin = _parse_date(fin_param, date.today())
    entrees = SoinSante.query.filter(SoinSante.date_soin.between(date_debut, date_fin)) \
        .order_by(SoinSante.date_soin).all()
    return entrees, date_debut, date_fin


@caille_bp.route("/rapports/sante.pdf")
def rapport_sante_pdf():
    entrees, date_debut, date_fin = _donnees_sante(request.args.get("debut"), request.args.get("fin"))
    buf = reports.rapport_sante(entrees, date_debut, date_fin, TYPES_SOIN)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"carnet_sante_{date_debut}_{date_fin}.pdf")


@caille_bp.route("/rapports/sante.xlsx")
def rapport_sante_excel():
    entrees, date_debut, date_fin = _donnees_sante(request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_sante(entrees, TYPES_SOIN)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"carnet_sante_{date_debut}_{date_fin}.xlsx")


# ---- Clients ----
@caille_bp.route("/rapports/clients.pdf")
def rapport_clients_pdf():
    liste = Client.query.order_by(Client.nom).all()
    buf = reports.rapport_clients(liste)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="clients.pdf")


@caille_bp.route("/rapports/clients.xlsx")
def rapport_clients_excel():
    liste = Client.query.order_by(Client.nom).all()
    buf = excel_reports.excel_clients(liste)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True, download_name="clients.xlsx")


# ---- Ventes ----
def _donnees_ventes(debut_param, fin_param):
    date_debut = _parse_date(debut_param, date.today() - timedelta(days=29))
    date_fin = _parse_date(fin_param, date.today())
    entrees = Vente.query.filter(Vente.date_vente.between(date_debut, date_fin)) \
        .order_by(Vente.date_vente).all()
    total = round(sum(v.montant_total for v in entrees), 2)
    return entrees, date_debut, date_fin, total


@caille_bp.route("/rapports/ventes.pdf")
def rapport_ventes_pdf():
    entrees, date_debut, date_fin, total = _donnees_ventes(request.args.get("debut"), request.args.get("fin"))
    buf = reports.rapport_ventes(entrees, date_debut, date_fin, total)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                      download_name=f"rapport_ventes_{date_debut}_{date_fin}.pdf")


@caille_bp.route("/rapports/ventes.xlsx")
def rapport_ventes_excel():
    entrees, date_debut, date_fin, total = _donnees_ventes(request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_ventes(entrees, total)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"rapport_ventes_{date_debut}_{date_fin}.xlsx")


# ---- Croissance ----
@caille_bp.route("/rapports/croissance.pdf")
def rapport_croissance_pdf():
    lot_id = request.args.get("lot_id")
    query = PeseeCroissance.query
    lot_nom = None
    if lot_id:
        query = query.filter_by(lot_id=_parse_int(lot_id))
        lot = Lot.query.get(_parse_int(lot_id))
        lot_nom = lot.nom if lot else None
    entrees = query.order_by(PeseeCroissance.date_pesee).all()
    buf = reports.rapport_croissance(entrees, lot_nom)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="suivi_croissance.pdf")


@caille_bp.route("/rapports/croissance.xlsx")
def rapport_croissance_excel():
    lot_id = request.args.get("lot_id")
    query = PeseeCroissance.query
    if lot_id:
        query = query.filter_by(lot_id=_parse_int(lot_id))
    entrees = query.order_by(PeseeCroissance.date_pesee).all()
    buf = excel_reports.excel_croissance(entrees)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True, download_name="suivi_croissance.xlsx")


# ---------------------------------------------------------------------------
# RENTABILITÉ (indice de consommation, revenu - coût provende)
# ---------------------------------------------------------------------------
def _donnees_rentabilite(debut_param, fin_param):
    date_debut = _parse_date(debut_param, date.today() - timedelta(days=364))
    date_fin = _parse_date(fin_param, date.today())

    lots_tous = Lot.query.order_by(Lot.nom).all()

    pontes = SuiviPonte.query.filter(SuiviPonte.date_jour.between(date_debut, date_fin)).all()
    ventes_periode = Vente.query.filter(Vente.date_vente.between(date_debut, date_fin)).all()
    achats = AchatProvende.query.filter(AchatProvende.date_achat.between(date_debut, date_fin)).all()
    depenses_periode = Depense.query.filter(Depense.date_depense.between(date_debut, date_fin)).all()

    mensuel = {}
    for p in pontes:
        cle = p.date_jour.strftime("%Y-%m")
        mensuel.setdefault(cle, {"revenu": 0.0, "cout_provende": 0.0, "depenses": 0.0})
        mensuel[cle]["revenu"] += p.montant_vente
    for v in ventes_periode:
        cle = v.date_vente.strftime("%Y-%m")
        mensuel.setdefault(cle, {"revenu": 0.0, "cout_provende": 0.0, "depenses": 0.0})
        mensuel[cle]["revenu"] += v.montant_total
    for a in achats:
        cle = a.date_achat.strftime("%Y-%m")
        mensuel.setdefault(cle, {"revenu": 0.0, "cout_provende": 0.0, "depenses": 0.0})
        mensuel[cle]["cout_provende"] += (a.prix_total or 0)
    for d in depenses_periode:
        cle = d.date_depense.strftime("%Y-%m")
        mensuel.setdefault(cle, {"revenu": 0.0, "cout_provende": 0.0, "depenses": 0.0})
        mensuel[cle]["depenses"] += (d.montant or 0)

    stats_mensuelles = []
    for cle in sorted(mensuel.keys()):
        r = round(mensuel[cle]["revenu"], 2)
        cp = round(mensuel[cle]["cout_provende"], 2)
        dep = round(mensuel[cle]["depenses"], 2)
        stats_mensuelles.append({
            "mois": cle, "revenu": r, "cout_provende": cp, "depenses": dep,
            "marge": round(r - cp - dep, 2),
        })

    return lots_tous, stats_mensuelles, date_debut, date_fin


@caille_bp.route("/rentabilite")
def rentabilite():
    lots_tous, stats_mensuelles, date_debut, date_fin = _donnees_rentabilite(
        request.args.get("debut"), request.args.get("fin"))
    return render_template("rentabilite.html", lots=lots_tous, stats_mensuelles=stats_mensuelles,
                            date_debut=date_debut, date_fin=date_fin)


@caille_bp.route("/rentabilite.xlsx")
def rentabilite_excel():
    lots_tous, stats_mensuelles, date_debut, date_fin = _donnees_rentabilite(
        request.args.get("debut"), request.args.get("fin"))
    buf = excel_reports.excel_rentabilite(lots_tous, stats_mensuelles)
    return send_file(buf, mimetype=XLSX_MIME, as_attachment=True,
                      download_name=f"rentabilite_{date_debut}_{date_fin}.xlsx")