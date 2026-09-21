"""
seeds.py — Données initiales créées au premier démarrage (si les tables sont vides).
"""
import os

from extensions import db


def _seed_categories_si_vide():
    """Crée la catégorie « Aviculture » par défaut si aucune n'existe encore.
    D'autres catégories (Cuniculture, Porciculture, ...) peuvent être ajoutées
    librement depuis l'interface (page Catégories d'élevage)."""
    from models import CategorieElevage
    if CategorieElevage.query.count() == 0:
        db.session.add(CategorieElevage(
            nom="Aviculture", description="Élevage d'oiseaux (cailles, poules, canards...)",
            produit_des_oeufs=True,
        ))
        db.session.commit()


def _seed_especes_si_vide():
    """Crée l'espèce « Caille » par défaut si aucune n'existe encore.
    D'autres espèces (Poule, Lapin, ...) peuvent être ajoutées depuis
    l'interface (page Espèces / Types d'élevage)."""
    from models import Espece, CategorieElevage
    if Espece.query.count() == 0:
        aviculture = CategorieElevage.query.filter_by(nom="Aviculture").first()
        db.session.add(Espece(
            nom="Caille", description="Élevage de cailles (ponte / chair)",
            categorie_id=aviculture.id if aviculture else None,
        ))
        db.session.commit()


def _seed_types_provende_si_vide():
    """Pré-remplit les 3 types de provende classiques si la table est vide."""
    from models import TypeProvende
    if TypeProvende.query.count() == 0:
        defaults = [
            TypeProvende(nom="Démarrage", description="0 à 3 semaines, riche en protéines (~28%)", seuil_alerte_kg=15),
            TypeProvende(nom="Croissance", description="3 à 6 semaines (~22% protéines)", seuil_alerte_kg=15),
            TypeProvende(nom="Ponte", description="Dès l'entrée en ponte, avec calcium (~20% protéines)", seuil_alerte_kg=20),
        ]
        db.session.add_all(defaults)
        db.session.commit()


def _seed_admin_si_vide():
    """Crée un premier compte administrateur si aucun utilisateur n'existe.

    Identifiants configurables via les variables d'environnement
    ADMIN_USERNAME / ADMIN_PASSWORD. À défaut : admin / changeme123
    (à changer immédiatement après le premier déploiement)."""
    from models import User
    if User.query.count() == 0:
        username = os.environ.get("ADMIN_USERNAME", "admin")
        password = os.environ.get("ADMIN_PASSWORD", "changeme123")
        user = User(username=username, role="proprietaire", actif=True)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()


def seed_all():
    """À appeler dans un contexte d'application, après db.create_all()."""
    _seed_categories_si_vide()
    _seed_especes_si_vide()
    _seed_types_provende_si_vide()
    _seed_admin_si_vide()
