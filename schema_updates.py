"""
schema_updates.py — Mises à jour légères du schéma pour les bases DÉJÀ créées.

`db.create_all()` crée les tables manquantes mais n'ajoute jamais de colonne à une table
existante. Ce module ajoute les colonnes nécessaires (une seule fois, sans toucher aux
données). Pour une nouvelle base, create_all() crée déjà tout et ces fonctions ne font rien.

Pour ajouter une colonne plus tard : ajoutez une ligne dans appliquer().
"""
from sqlalchemy import inspect, text

from extensions import db


def _colonnes(table):
    return {c["name"] for c in inspect(db.engine).get_columns(table)}


def ajouter_colonne_si_absente(table, colonne, definition):
    """Ajoute `colonne` à `table` si elle n'existe pas. `definition` = type + contraintes."""
    if colonne in _colonnes(table):
        return False
    try:
        with db.engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {colonne} {definition}"))
    except Exception:
        # Deux instances qui démarrent en même temps : l'autre a peut-être déjà ajouté la colonne.
        if colonne in _colonnes(table):
            return False
        raise
    return True


def appliquer():
    vrai = "1" if db.engine.dialect.name == "sqlite" else "TRUE"
    # Rôles : les comptes existants (jusqu'ici tous administrateurs) deviennent « propriétaire ».
    ajouter_colonne_si_absente("caille_users", "role", "VARCHAR(20) NOT NULL DEFAULT 'proprietaire'")
    ajouter_colonne_si_absente("caille_users", "actif", f"BOOLEAN NOT NULL DEFAULT {vrai}")
