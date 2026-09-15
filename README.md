# Module « Gestion de caille » pour HITNA

Module Flask complet pour gérer l'élevage de cailles : ponte, ventes d'œufs,
mortalité, naissances de cailletons, provende (achats, consommation, stock,
alertes de réapprovisionnement), fournisseurs, cahier de charges (tâches et
protocoles), et archive des lots réformés.

## 1. Tester le module seul (avant intégration)

```bash
cd hitna_caille
pip install -r requirements.txt
python app.py
```

Ouvrez http://127.0.0.1:5000/caille/ — une base SQLite locale (`caille_test.db`)
est créée automatiquement, avec 3 types de provende pré-remplis (Démarrage,
Croissance, Ponte). Un compte admin est aussi créé automatiquement :
**identifiant `admin` / mot de passe `changeme123`** (à changer via les
variables d'environnement `ADMIN_USERNAME` / `ADMIN_PASSWORD` avant le tout
premier démarrage — voir section 4).

## 2. Intégrer dans l'application HITNA existante

### a) Copier les fichiers
Copiez dans votre projet HITNA :
- `models.py` → fusionnez son contenu dans votre `models.py` existant
  (ou importez-le comme fichier séparé, ex. `models_caille.py`)
- `routes/caille.py` → dans votre dossier `routes/`
- `templates/caille/` → dans votre dossier `templates/`
- `static/caille/style.css` → dans votre dossier `static/`

### b) Réutiliser votre objet `db` existant
Ce module ne doit PAS créer un second objet SQLAlchemy. Dans `models.py` et
`routes/caille.py`, remplacez :
```python
from extensions import db
```
par l'import de l'objet `db` déjà utilisé dans votre application HITNA
(généralement défini dans `app.py` ou `extensions.py` de HITNA). Supprimez
alors le fichier `extensions.py` fourni ici — il n'est utile que pour les
tests autonomes.

### c) Enregistrer le blueprint
Dans votre `app.py` principal :
```python
from routes.caille import caille_bp
app.register_blueprint(caille_bp)
```

### d) Créer les tables
Toutes les tables du module sont préfixées `caille_` pour ne jamais entrer
en conflit avec vos tables existantes (produits, ventes, employés...).
- Si HITNA utilise Flask-Migrate : `flask db migrate -m "ajout module caille"` puis `flask db upgrade`
- Sinon, un simple `db.create_all()` dans le contexte de l'app créera les
  nouvelles tables sans toucher aux tables existantes.

### e) Protéger l'accès (authentification)
Ce module a désormais sa propre authentification (`routes/auth.py`, modèle
`User` dans `models.py`, pages `/login` et `/logout`). Si HITNA a déjà son
propre système de connexion (Flask-Login ou autre), deux options :
- **Le plus simple** : garder l'auth du module telle quelle (elle est
  indépendante et ne touche à rien d'autre).
- **Pour fusionner** : retirez `routes/auth.py`, le modèle `User`, et le
  `@caille_bp.before_request` dans `routes/caille.py` (qui vérifie
  `current_user.is_authenticated`), puis protégez chaque route avec le
  `@login_required` de votre système HITNA existant.

### f) Lien dans le menu HITNA
Ajoutez un lien « Gestion caille » dans la navigation principale de HITNA
pointant vers `{{ url_for('caille.dashboard') }}`.

## 3. Variables d'environnement

| Variable | Rôle | Défaut si absente |
|---|---|---|
| `DATABASE_URL` | Connexion PostgreSQL (Neon, Supabase...) | SQLite local (⚠️ ne persiste pas sur Vercel) |
| `SECRET_KEY` | Clé de session Flask | valeur de dev non sécurisée — **à définir en prod** |
| `ADMIN_USERNAME` | Identifiant du premier compte créé automatiquement | `admin` |
| `ADMIN_PASSWORD` | Mot de passe du premier compte créé automatiquement | `changeme123` — **à changer** |

Ces deux dernières variables ne servent qu'à la toute première création de
compte (quand la table utilisateurs est vide). Pour ajouter d'autres
comptes ou changer un mot de passe ensuite, il faut le faire directement en
base ou ajouter une petite page de gestion des comptes (non incluse ici).

## 4. Fonctionnalités couvertes

| Besoin exprimé | Où le trouver |
|---|---|
| Œufs pondus / vendus par jour | Ponte & ventes d'œufs |
| Cailletons (naissances) | Cailletons (naissances) |
| Cailles et cailletons morts par jour | Mortalité |
| Kg de provende acheté par jour/période, quel type acheter | Provende → Types + Achats |
| Stock de provende et alerte de réapprovisionnement | Tableau de bord + Provende → Types |
| Réapprovisionnement (fournisseurs, commandes) | Provende → Achats + Fournisseurs |
| Cahier de charges | Cahier de charges (tâches, protocoles, récurrence, catégories) |
| Archive | Archive (lots réformés, historique conservé) |
| Suivi par lot / bâtiment | Lots de cailles (effectif, historique, détail) |
| Revenu des ventes d'œufs | Calculé automatiquement (dashboard + page ponte + détail lot) |
| Coût de la provende | Calculé automatiquement (page achats) |
| Authentification | Page `/login`, session Flask-Login, toutes les pages du module protégées |
| Graphique de ponte | Page Statistiques (courbe pondus/vendus + barres mortalité, filtrables par période et par lot) |
| Export PDF | Page Rapports PDF (ponte, mortalité, achats de provende, fiche d'un lot) |

## 5. Idées d'évolutions possibles (non incluses ici)

- Notifications automatiques (email/SMS) quand un seuil de provende est atteint
- Calcul automatique de l'indice de consommation (kg provende / œuf produit)
- Rattachement des ventes d'œufs au système de vente général de HITNA si les
  œufs sont aussi vendus via le module boutique existant
- Page de gestion des comptes (créer/désactiver des utilisateurs depuis l'interface)