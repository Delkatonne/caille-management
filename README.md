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
Croissance, Ponte) pour que le tableau de bord ne soit pas vide.

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
Si vos autres routes HITNA utilisent `@login_required` (Flask-Login), ajoutez
ce même décorateur sur chaque fonction de `routes/caille.py`, et pensez à
ajouter un lien vers `/caille/` dans le menu principal de HITNA.

### f) Lien dans le menu HITNA
Ajoutez un lien « Gestion caille » dans la navigation principale de HITNA
pointant vers `{{ url_for('caille.dashboard') }}`.

## 3. Fonctionnalités couvertes

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

## 4. Idées d'évolutions possibles (non incluses ici)

- Export PDF/Excel des rapports (vous avez déjà des PDF dans HITNA — le module
  peut réutiliser la même logique)
- Notifications automatiques (email/SMS) quand un seuil de provende est atteint
- Courbe de ponte / mortalité (graphique) par lot
- Calcul automatique de l'indice de consommation (kg provende / œuf produit)
- Rattachement des ventes d'œufs au système de vente général de HITNA si les
  œufs sont aussi vendus via le module boutique existant
