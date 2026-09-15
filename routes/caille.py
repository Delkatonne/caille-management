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

from flask import Blueprint, render_template, request, redirect, url_for, flash

from extensions import db
from models import (
    Lot, SuiviPonte, SuiviMortalite, Naissance,
    TypeProvende, Fournisseur, AchatProvende, ConsommationProvende,
    Tache, stock_oeufs_actuel,
)

caille_bp = Blueprint(
    "caille", __name__,
    url_prefix="/caille",
    template_folder="../templates/caille",
    static_folder="../static/caille",
)


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
    oeufs_vendus_jour = sum(p.oeufs_vendus for p in ponte_jour)
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
    return render_template("lots.html", lots=liste_lots, filtre_statut=filtre_statut)


@caille_bp.route("/lots/<int:lot_id>/modifier", methods=["POST"])
def modifier_lot(lot_id):
    lot = Lot.query.get_or_404(lot_id)
    lot.nom = request.form.get("nom", lot.nom).strip()
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
    return render_template("lot_detail.html", lot=lot, pontes=pontes, mortalites=mortalites, naissances=naissances)


# ---------------------------------------------------------------------------
# PONTE / VENTE D'ŒUFS
# ---------------------------------------------------------------------------
@caille_bp.route("/ponte", methods=["GET", "POST"])
def ponte():
    if request.method == "POST":
        lot_id = _parse_int(request.form.get("lot_id"))
        date_jour = _parse_date(request.form.get("date_jour"))
        entree = SuiviPonte.query.filter_by(lot_id=lot_id, date_jour=date_jour).first()
        if entree is None:
            entree = SuiviPonte(lot_id=lot_id, date_jour=date_jour)
            db.session.add(entree)
        entree.oeufs_pondus = _parse_int(request.form.get("oeufs_pondus"))
        entree.oeufs_vendus = _parse_int(request.form.get("oeufs_vendus"))
        entree.prix_unitaire_vente = _parse_float(request.form.get("prix_unitaire_vente"))
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
    entrees = query.order_by(SuiviPonte.date_jour.desc()).all()

    totaux = {
        "pondus": sum(e.oeufs_pondus for e in entrees),
        "vendus": sum(e.oeufs_vendus for e in entrees),
        "casses": sum(e.oeufs_casses for e in entrees),
        "revenu": round(sum(e.montant_vente for e in entrees), 2),
    }

    lots_actifs = Lot.query.filter(Lot.statut != "archive").order_by(Lot.nom).all()
    return render_template(
        "ponte.html", entrees=entrees, lots=lots_actifs, totaux=totaux,
        date_debut=date_debut, date_fin=date_fin, lot_filtre=lot_filtre,
        stock_oeufs=stock_oeufs_actuel(),
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
    return render_template("taches.html", taches=liste, lots=lots_actifs, filtre_statut=filtre_statut)


@caille_bp.route("/taches/<int:tache_id>/statut", methods=["POST"])
def changer_statut_tache(tache_id):
    t = Tache.query.get_or_404(tache_id)
    nouveau_statut = request.form.get("statut", "a_faire")
    t.statut = nouveau_statut
    if nouveau_statut == "fait":
        t.date_realisation = date.today()
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
