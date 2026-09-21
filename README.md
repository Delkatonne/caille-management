# HITNA Ferme — application de gestion de la ferme

Application Flask + PostgreSQL (SQLite en local) pour gérer la ferme Hitna :
lots d'animaux, ponte et ventes d'œufs, mortalité, naissances, croissance, santé,
provende (achats, consommation, alertes de stock), clients, ventes, fournisseurs,
dépenses, rentabilité, personnel, cahier de charges, statistiques et rapports PDF / Excel.

Cette application est **indépendante** de l'application de gestion des boutiques HITNA
(dépôt, base de données et déploiement séparés).

## Lancer en local

```bash
pip install -r requirements.txt
python app.py
```

Ouvrez http://127.0.0.1:5000/ — une base SQLite locale (`caille_test.db`) est créée
automatiquement, avec les données de départ (catégorie Aviculture, espèce Caille,
3 types de provende) et un compte **admin / changeme123** de rôle *propriétaire* (à changer, voir plus bas).

## Architecture

Un blueprint par bloc fonctionnel, chacun avec ses routes (dans `blueprints/`) et ses
templates (dans `templates/<blueprint>/`) :

```
hitna_ferme/
  app.py               création de l'app, config, protection par connexion
  extensions.py        db (SQLAlchemy) et login_manager
  models.py            toutes les tables (préfixe caille_)
  seeds.py             données initiales (si tables vides)
  permissions.py       rôles et droits d'accès (qui peut voir / faire quoi)
  schema_updates.py    ajout automatique des nouvelles colonnes aux bases déjà créées
  utils.py             parse_date / parse_int / parse_float, XLSX_MIME
  blueprints/
    auth/              connexion, déconnexion, mot de passe, gestion des utilisateurs et rôles
    dashboard/         home (tableau de bord), statistiques, rapports (PDF/Excel)
    production/        lots (+ archive), especes (+ catégories), ponte, mortalite,
                       naissances, croissance, sante
    stocks/            provende (types, achats, consommation)
    finances/          clients, ventes, fournisseurs, depenses, rentabilite
    personnel/         employes, taches (cahier de charges)
  services/            reports.py (PDF, reportlab), excel_reports.py (openpyxl)
  templates/           base.html + un dossier par blueprint
  static/              css/style.css, img/logo-hitna.jpg
```

### Rôles et droits

Trois rôles, chacun ayant les droits du rôle inférieur. Le propriétaire crée les comptes dans
**Administration → Utilisateurs & rôles**.

| | Employé | Gérant | Propriétaire |
|---|:-:|:-:|:-:|
| Tableau de bord (sans les chiffres d'argent pour l'employé) | ✅ | ✅ | ✅ |
| Saisie : ponte, mortalité, naissances, croissance, santé, consommation d'aliment | ✅ | ✅ | ✅ |
| Voir les lots, les stocks d'aliment, ses tâches et les faire avancer | ✅ | ✅ | ✅ |
| Créer/modifier/archiver des lots, espèces et catégories | — | ✅ | ✅ |
| Achats d'aliment, types d'alimentation | — | ✅ | ✅ |
| Clients, ventes, dépenses, fournisseurs | — | ✅ | ✅ |
| Personnel, création de tâches | — | ✅ | ✅ |
| Statistiques et rapports PDF / Excel | — | ✅ | ✅ |
| Supprimer une entrée de ponte, de santé, de pesée | — | ✅ | ✅ |
| Rentabilité, supprimer une vente ou une dépense | — | — | ✅ |
| Gérer les comptes et les rôles | — | — | ✅ |

- Les règles sont appliquées **côté serveur** (`permissions.py`) : masquer un bouton ne suffit pas,
  une page interdite renvoie « Accès refusé » même si on tape son adresse.
- Un compte **désactivé** ne peut plus se connecter (immédiatement) mais son historique est conservé.
- Le propriétaire ne peut ni changer son propre rôle ni désactiver son propre compte.
- Les comptes existants avant cette mise à jour deviennent automatiquement **propriétaire**
  (les colonnes `role` et `actif` sont ajoutées au démarrage, sans perte de données).
- Nouvelle page : elle hérite du niveau de son blueprint (`PAR_BLUEPRINT`). Pour un cas particulier,
  ajoutez une ligne dans `PAR_ENDPOINT` (ou `PAR_ENDPOINT_ECRITURE` pour les envois de formulaire).
  Un nom de page inexistant dans ces tables fait échouer le démarrage, pour éviter une règle ignorée.
- Dans un template : `{% if peut('gerant') %}...{% endif %}` masque un élément aux employés.

## Ajouter une fonctionnalité dans un bloc existant
1. Créez `blueprints/<bloc>/mon_module.py` avec `from . import bp` puis vos routes `@bp.route(...)`.
2. Ajoutez `mon_module` à la ligne `from . import ...` de `blueprints/<bloc>/__init__.py`.
3. Créez le template dans `templates/<bloc>/` et appelez-le avec `render_template("<bloc>/mon_page.html")`.
4. Ajoutez le lien dans `templates/base.html` avec `{{ nav('<bloc>.ma_fonction', 'icone', 'Libellé') }}`.

### Ajouter un nouveau bloc
Copiez le dossier d'un petit blueprint (ex. `personnel/`), changez le nom dans `Blueprint("nom", __name__)`,
puis ajoutez-le dans `blueprints/__init__.py` (`register_blueprints`).

### Modèles de données
Toutes les tables sont dans `models.py` (préfixe `caille_`). Les noms de tables n'ont **pas** changé :
aucune migration n'est nécessaire, vos données existantes restent intactes.

## Variables d'environnement

| Variable | Rôle | Défaut si absente |
|---|---|---|
| `DATABASE_URL` | Connexion PostgreSQL (Neon, Supabase...) | SQLite local (⚠️ ne persiste pas sur Vercel) |
| `SECRET_KEY` | Clé de session Flask | valeur de dev non sécurisée — **à définir en prod** |
| `ADMIN_USERNAME` | Identifiant du premier compte créé automatiquement | `admin` |
| `ADMIN_PASSWORD` | Mot de passe du premier compte créé automatiquement | `changeme123` — **à changer** |

`ADMIN_USERNAME` / `ADMIN_PASSWORD` ne servent qu'à la toute première création de compte
(table utilisateurs vide). Ensuite, changez le mot de passe depuis « Changer le mot de passe ».

## Où trouver chaque fonctionnalité

| Besoin | Menu | Blueprint |
|---|---|---|
| Lots, espèces, catégories, archive | Production | `production` |
| Œufs pondus / vendus, mortalité, naissances, croissance, santé | Production | `production` |
| Types d'alimentation, achats, consommation, alertes de stock | Stocks | `stocks` |
| Fournisseurs, clients, ventes, dépenses, rentabilité | Finances | `finances` |
| Personnel, cahier de charges | Personnel | `personnel` |
| Tableau de bord, statistiques, rapports PDF / Excel | Pilotage | `dashboard` |

## Changements par rapport à l'ancienne version (module « caille »)

- Le fichier `routes/caille.py` (1 300 lignes) est découpé en modules par blueprint.
- Les adresses n'ont plus le préfixe `/caille` (ex. `/caille/lots` → `/lots`).
  Les anciennes adresses redirigent automatiquement vers les nouvelles.
- Le menu est regroupé par bloc : Production, Stocks, Finances, Personnel, Pilotage.
- `static/caille/` → `static/css/` et `static/img/`.
- `reports.py` et `excel_reports.py` → `services/`.
- Nouveau : **rôles** propriétaire / gérant / employé (voir plus haut).
- Sécurité : après connexion, la redirection `?next=` n'accepte plus que les adresses internes.
- Correction : la page **Clients** plantait (template `clients.html` absent) — il a été créé.
- Correction : la fiche d'une espèce plantait (la route cherchait `espece_detail.html`, le fichier
  s'appelait `especes_detail.html`).
- Correction : les adresses des rapports dans `rapports.html` étaient écrites en dur ; elles sont
  maintenant générées par `url_for`.
