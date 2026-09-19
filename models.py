"""
models.py — Module "Gestion de caille" pour HITNA
====================================================
Toutes les tables sont préfixées `caille_` pour ne jamais entrer en conflit
avec les tables existantes de l'application HITNA.

Rien n'est jamais supprimé physiquement dans ce module : un Lot "terminé"
passe au statut ARCHIVE plutôt que d'être supprimé, afin de conserver
l'historique complet (production, mortalité, consommation) pour les
rapports et les statistiques.
"""
from datetime import date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


# ---------------------------------------------------------------------------
# UTILISATEURS (authentification)
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = "caille_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ---------------------------------------------------------------------------
# LOTS (bandes de cailles)
# ---------------------------------------------------------------------------
class Espece(db.Model):
    """Type d'élevage géré (Caille, Poule, Lapin, ...). Permet d'ajouter
    facilement d'autres sujets gérés que la caille, sans changer le modèle."""
    __tablename__ = "caille_especes"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(80), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)

    lots = db.relationship("Lot", backref="espece", lazy="dynamic")


class Lot(db.Model):
    __tablename__ = "caille_lots"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    espece_id = db.Column(db.Integer, db.ForeignKey("caille_especes.id"), nullable=True)
    type_lot = db.Column(db.String(20), nullable=False, default="ponte")  # ponte, chair, reproduction
    date_mise_en_place = db.Column(db.Date, nullable=False, default=date.today)
    effectif_initial = db.Column(db.Integer, nullable=False, default=0)
    statut = db.Column(db.String(20), nullable=False, default="actif")  # actif, reforme, archive
    date_reforme = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    date_creation = db.Column(db.DateTime, default=db.func.now())

    pontes = db.relationship("SuiviPonte", backref="lot", lazy="dynamic", cascade="all, delete-orphan")
    mortalites = db.relationship("SuiviMortalite", backref="lot", lazy="dynamic", cascade="all, delete-orphan")
    naissances = db.relationship("Naissance", backref="lot", lazy="dynamic", cascade="all, delete-orphan")
    consommations = db.relationship("ConsommationProvende", backref="lot", lazy="dynamic")
    taches = db.relationship("Tache", backref="lot", lazy="dynamic")
    depenses = db.relationship("Depense", backref="lot", lazy="dynamic")

    # ---- Statistiques calculées ----
    @property
    def total_mortalite_cailles(self):
        return db.session.query(db.func.coalesce(db.func.sum(SuiviMortalite.cailles_mortes), 0)) \
            .filter(SuiviMortalite.lot_id == self.id).scalar()

    @property
    def total_mortalite_cailletons(self):
        return db.session.query(db.func.coalesce(db.func.sum(SuiviMortalite.cailletons_morts), 0)) \
            .filter(SuiviMortalite.lot_id == self.id).scalar()

    @property
    def total_naissances(self):
        return db.session.query(db.func.coalesce(db.func.sum(Naissance.nombre_cailletons), 0)) \
            .filter(Naissance.lot_id == self.id).scalar()

    @property
    def effectif_actuel(self):
        return (self.effectif_initial or 0) + (self.total_naissances or 0) \
            - (self.total_mortalite_cailles or 0) - (self.total_mortalite_cailletons or 0)

    @property
    def total_oeufs_pondus(self):
        return db.session.query(db.func.coalesce(db.func.sum(SuiviPonte.oeufs_pondus), 0)) \
            .filter(SuiviPonte.lot_id == self.id).scalar()

    @property
    def total_oeufs_vendus(self):
        return db.session.query(db.func.coalesce(db.func.sum(SuiviPonte.oeufs_vendus), 0)) \
            .filter(SuiviPonte.lot_id == self.id).scalar()

    @property
    def total_revenu_oeufs(self):
        rows = SuiviPonte.query.filter_by(lot_id=self.id).all()
        return round(sum((r.oeufs_vendus or 0) * (r.prix_unitaire_vente or 0) for r in rows), 2)

    @property
    def total_consommation_kg(self):
        return round(db.session.query(db.func.coalesce(db.func.sum(ConsommationProvende.quantite_kg), 0))
                     .filter(ConsommationProvende.lot_id == self.id).scalar(), 2)

    @property
    def indice_consommation(self):
        """Kg de provende consommée par œuf produit (plus bas = plus efficace).
        Repère indicatif en aviculture : autour de 0,25-0,35 kg/œuf pour la caille."""
        if self.total_oeufs_pondus:
            return round((self.total_consommation_kg or 0) / self.total_oeufs_pondus, 3)
        return None

    @property
    def cout_provende_estime(self):
        """Coût de la provende consommée par ce lot, estimé à partir du prix
        d'achat moyen (pondéré) de chaque type de provende consommé."""
        total = 0.0
        for c in self.consommations:
            total += (c.quantite_kg or 0) * c.type_provende.prix_moyen_achat_kg
        return round(total, 2)

    @property
    def total_depenses(self):
        """Autres dépenses liées à ce lot (vaccination, médicament, transport...)."""
        return round(db.session.query(db.func.coalesce(db.func.sum(Depense.montant), 0))
                     .filter(Depense.lot_id == self.id).scalar(), 2)

    @property
    def marge_estimee(self):
        """Revenu des ventes d'œufs moins le coût estimé de la provende consommée
        et les autres dépenses (vaccination, médicament, transport...) du lot."""
        return round((self.total_revenu_oeufs or 0) - (self.cout_provende_estime or 0)
                     - (self.total_depenses or 0), 2)


# ---------------------------------------------------------------------------
# PONTE / VENTE D'ŒUFS (journalier)
# ---------------------------------------------------------------------------
class SuiviPonte(db.Model):
    __tablename__ = "caille_suivi_ponte"
    __table_args__ = (db.UniqueConstraint("lot_id", "date_jour", name="uq_ponte_lot_date"),)

    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey("caille_lots.id"), nullable=False)
    date_jour = db.Column(db.Date, nullable=False, default=date.today)
    oeufs_pondus = db.Column(db.Integer, nullable=False, default=0)
    oeufs_vendus = db.Column(db.Integer, nullable=False, default=0)
    prix_unitaire_vente = db.Column(db.Float, nullable=False, default=0)
    oeufs_casses = db.Column(db.Integer, nullable=False, default=0)
    oeufs_autoconsommes = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)

    @property
    def montant_vente(self):
        return round((self.oeufs_vendus or 0) * (self.prix_unitaire_vente or 0), 2)

    @property
    def solde_jour(self):
        """Œufs du jour non vendus/cassés/autoconsommés -> vont au stock."""
        return (self.oeufs_pondus or 0) - (self.oeufs_vendus or 0) \
            - (self.oeufs_casses or 0) - (self.oeufs_autoconsommes or 0)


def stock_oeufs_actuel():
    """Stock global d'œufs = somme cumulée de tous les soldes journaliers."""
    rows = SuiviPonte.query.all()
    return sum(r.solde_jour for r in rows)


# ---------------------------------------------------------------------------
# MORTALITÉ (cailles adultes + cailletons)
# ---------------------------------------------------------------------------
class SuiviMortalite(db.Model):
    __tablename__ = "caille_suivi_mortalite"
    __table_args__ = (db.UniqueConstraint("lot_id", "date_jour", name="uq_mortalite_lot_date"),)

    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey("caille_lots.id"), nullable=False)
    date_jour = db.Column(db.Date, nullable=False, default=date.today)
    cailles_mortes = db.Column(db.Integer, nullable=False, default=0)      # adultes
    cailletons_morts = db.Column(db.Integer, nullable=False, default=0)    # jeunes
    cause = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)


# ---------------------------------------------------------------------------
# NAISSANCES / ÉCLOSIONS DE CAILLETONS
# ---------------------------------------------------------------------------
class Naissance(db.Model):
    __tablename__ = "caille_naissances"

    id = db.Column(db.Integer, primary_key=True)
    lot_id = db.Column(db.Integer, db.ForeignKey("caille_lots.id"), nullable=False)
    date_jour = db.Column(db.Date, nullable=False, default=date.today)
    nombre_cailletons = db.Column(db.Integer, nullable=False, default=0)
    origine = db.Column(db.String(20), nullable=False, default="eclosion")  # eclosion, achat
    notes = db.Column(db.Text, nullable=True)


# ---------------------------------------------------------------------------
# PROVENDE (aliment) : types, fournisseurs, achats, consommation
# ---------------------------------------------------------------------------
class TypeProvende(db.Model):
    __tablename__ = "caille_type_provende"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False, unique=True)  # Démarrage, Croissance, Ponte...
    description = db.Column(db.Text, nullable=True)
    seuil_alerte_kg = db.Column(db.Float, nullable=False, default=20)
    actif = db.Column(db.Boolean, nullable=False, default=True)

    achats = db.relationship("AchatProvende", backref="type_provende", lazy="dynamic")
    consommations = db.relationship("ConsommationProvende", backref="type_provende", lazy="dynamic")

    @property
    def total_achete_kg(self):
        return db.session.query(db.func.coalesce(db.func.sum(AchatProvende.quantite_kg), 0)) \
            .filter(AchatProvende.type_provende_id == self.id).scalar()

    @property
    def total_consomme_kg(self):
        return db.session.query(db.func.coalesce(db.func.sum(ConsommationProvende.quantite_kg), 0)) \
            .filter(ConsommationProvende.type_provende_id == self.id).scalar()

    @property
    def stock_actuel_kg(self):
        return round((self.total_achete_kg or 0) - (self.total_consomme_kg or 0), 2)

    @property
    def prix_moyen_achat_kg(self):
        """Prix moyen pondéré payé au kg, calculé sur l'historique des achats."""
        total_kg = self.total_achete_kg
        if not total_kg:
            return 0.0
        total_cout = db.session.query(db.func.coalesce(db.func.sum(AchatProvende.prix_total), 0)) \
            .filter(AchatProvende.type_provende_id == self.id).scalar()
        return round((total_cout or 0) / total_kg, 2)

    @property
    def en_alerte(self):
        return self.stock_actuel_kg <= self.seuil_alerte_kg


class Fournisseur(db.Model):
    __tablename__ = "caille_fournisseurs"

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(150), nullable=False)
    contact = db.Column(db.String(100), nullable=True)
    adresse = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    achats = db.relationship("AchatProvende", backref="fournisseur", lazy="dynamic")


class AchatProvende(db.Model):
    __tablename__ = "caille_achats_provende"

    id = db.Column(db.Integer, primary_key=True)
    date_achat = db.Column(db.Date, nullable=False, default=date.today)
    type_provende_id = db.Column(db.Integer, db.ForeignKey("caille_type_provende.id"), nullable=False)
    fournisseur_id = db.Column(db.Integer, db.ForeignKey("caille_fournisseurs.id"), nullable=True)
    quantite_kg = db.Column(db.Float, nullable=False, default=0)
    prix_total = db.Column(db.Float, nullable=True, default=0)
    notes = db.Column(db.Text, nullable=True)

    @property
    def prix_unitaire_kg(self):
        if self.quantite_kg:
            return round((self.prix_total or 0) / self.quantite_kg, 2)
        return 0


class ConsommationProvende(db.Model):
    __tablename__ = "caille_consommation_provende"

    id = db.Column(db.Integer, primary_key=True)
    date_jour = db.Column(db.Date, nullable=False, default=date.today)
    lot_id = db.Column(db.Integer, db.ForeignKey("caille_lots.id"), nullable=True)
    type_provende_id = db.Column(db.Integer, db.ForeignKey("caille_type_provende.id"), nullable=False)
    quantite_kg = db.Column(db.Float, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)


# ---------------------------------------------------------------------------
# CAHIER DE CHARGES : tâches, protocoles, rappels
# ---------------------------------------------------------------------------
class Tache(db.Model):
    __tablename__ = "caille_taches"

    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    categorie = db.Column(db.String(50), nullable=False, default="general")
    # general, sanitaire, entretien, alimentation, vente, reapprovisionnement
    date_prevue = db.Column(db.Date, nullable=True)
    date_realisation = db.Column(db.Date, nullable=True)
    recurrence = db.Column(db.String(20), nullable=True, default="aucune")  # aucune, quotidien, hebdo, mensuel
    statut = db.Column(db.String(20), nullable=False, default="a_faire")  # a_faire, en_cours, fait
    lot_id = db.Column(db.Integer, db.ForeignKey("caille_lots.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)


# ---------------------------------------------------------------------------
# DÉPENSES DIVERSES (vaccination, médicament, transport, matériel...)
# ---------------------------------------------------------------------------
class Depense(db.Model):
    """Toute dépense en dehors de la provende : vaccination, médicament,
    transport, matériel, main d'œuvre... La catégorie est en texte libre —
    l'utilisateur saisit lui-même ce dans quoi il a dépensé."""
    __tablename__ = "caille_depenses"

    id = db.Column(db.Integer, primary_key=True)
    date_depense = db.Column(db.Date, nullable=False, default=date.today)
    categorie = db.Column(db.String(100), nullable=False)  # ex: Vaccination, Médicament, Transport...
    montant = db.Column(db.Float, nullable=False, default=0)
    lot_id = db.Column(db.Integer, db.ForeignKey("caille_lots.id"), nullable=True)
    notes = db.Column(db.Text, nullable=True)