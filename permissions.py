"""
permissions.py — Rôles et droits d'accès.

Trois rôles hiérarchiques : chaque rôle a tous les droits du rôle inférieur.

    employe      saisie quotidienne (ponte, mortalité, naissances, croissance, santé,
                 consommation de provende) et consultation/mise à jour de ses tâches
    gerant       tout ce qui précède + gestion courante (lots, espèces, achats, clients,
                 ventes, dépenses, fournisseurs, personnel, statistiques, rapports, suppressions)
    proprietaire tout + rentabilité, suppression des ventes/dépenses, gestion des utilisateurs

Les règles sont appliquées à un seul endroit (app.py, avant chaque requête) :
le niveau minimum d'une page se cherche dans cet ordre :
    1. PAR_ENDPOINT_ECRITURE (envois de formulaire POST) si la requête modifie des données
    2. PAR_ENDPOINT
    3. PAR_BLUEPRINT
    4. à défaut : propriétaire (refus par défaut)
"""
EMPLOYE = "employe"
GERANT = "gerant"
PROPRIETAIRE = "proprietaire"

ROLES = {EMPLOYE: 1, GERANT: 2, PROPRIETAIRE: 3}
LIBELLES = {EMPLOYE: "Employé", GERANT: "Gérant", PROPRIETAIRE: "Propriétaire"}

# Pages accessibles sans connexion
ENDPOINTS_PUBLICS = {"auth.login", "ancienne_url"}

# Niveau par défaut d'un blueprint entier
PAR_BLUEPRINT = {
    "auth": EMPLOYE,          # déconnexion, changement de mot de passe (login est public)
    "dashboard": GERANT,      # statistiques et rapports
    "production": EMPLOYE,    # saisie quotidienne
    "stocks": EMPLOYE,
    "finances": GERANT,
    "personnel": GERANT,
}

# Exceptions par page (dans les deux sens : plus ouvert ou plus strict que le blueprint)
PAR_ENDPOINT = {
    "dashboard.dashboard": EMPLOYE,

    # production : configuration, archivage et suppressions réservés au gérant
    "production.modifier_lot": GERANT,
    "production.archiver_lot": GERANT,
    "production.reactiver_lot": GERANT,
    "production.archive": GERANT,
    "production.especes": GERANT,
    "production.detail_espece": GERANT,
    "production.categories_elevage": GERANT,
    "production.basculer_produit_des_oeufs": GERANT,
    "production.supprimer_ponte": GERANT,
    "production.supprimer_soin": GERANT,
    "production.supprimer_pesee": GERANT,

    # stocks : les achats (argent) sont réservés au gérant
    "stocks.achats_provende": GERANT,
    "stocks.desactiver_type_provende": GERANT,

    # finances : le propriétaire seul voit la rentabilité et supprime des écritures
    "finances.rentabilite": PROPRIETAIRE,
    "finances.rentabilite_excel": PROPRIETAIRE,
    "finances.supprimer_vente": PROPRIETAIRE,
    "finances.supprimer_depense": PROPRIETAIRE,

    # personnel : un employé peut faire avancer une tâche (à faire / en cours / fait)
    "personnel.taches": EMPLOYE,
    "personnel.changer_statut_tache": EMPLOYE,

    # comptes utilisateurs
    "auth.utilisateurs": PROPRIETAIRE,
    "auth.changer_role_utilisateur": PROPRIETAIRE,
    "auth.basculer_actif_utilisateur": PROPRIETAIRE,
    "auth.reinitialiser_mot_de_passe": PROPRIETAIRE,
}

# Niveau requis pour ENVOYER un formulaire (POST...) sur ces pages
# (la consultation, elle, suit PAR_ENDPOINT / PAR_BLUEPRINT)
PAR_ENDPOINT_ECRITURE = {
    "production.lots": GERANT,          # créer un lot
    "stocks.types_provende": GERANT,    # créer un type d'alimentation
    "personnel.taches": GERANT,         # créer une tâche
}

_METHODES_LECTURE = {"GET", "HEAD", "OPTIONS"}


def niveau(role):
    """Niveau numérique d'un rôle (0 si inconnu : aucun droit)."""
    return ROLES.get(role, 0)


def role_minimum(endpoint, methode="GET"):
    blueprint = endpoint.split(".", 1)[0] if "." in endpoint else None
    if methode not in _METHODES_LECTURE and endpoint in PAR_ENDPOINT_ECRITURE:
        return PAR_ENDPOINT_ECRITURE[endpoint]
    if endpoint in PAR_ENDPOINT:
        return PAR_ENDPOINT[endpoint]
    if blueprint in PAR_BLUEPRINT:
        return PAR_BLUEPRINT[blueprint]
    return PROPRIETAIRE


def autorise(user, endpoint, methode="GET"):
    """True si `user` (avec un attribut .role) peut accéder à cette page."""
    return niveau(getattr(user, "role", None)) >= niveau(role_minimum(endpoint, methode))


def verifier_regles(app):
    """Échoue au démarrage si une règle référence une page inexistante (faute de frappe,
    page renommée...) : sans cela, la règle serait ignorée en silence."""
    endpoints = {r.endpoint for r in app.url_map.iter_rules()}
    inconnus = [e for table in (PAR_ENDPOINT, PAR_ENDPOINT_ECRITURE) for e in table if e not in endpoints]
    invalides = [v for table in (PAR_ENDPOINT, PAR_ENDPOINT_ECRITURE, PAR_BLUEPRINT)
                 for v in table.values() if v not in ROLES]
    if inconnus or invalides:
        raise RuntimeError(f"permissions.py : pages inconnues {inconnus} / rôles invalides {invalides}")
