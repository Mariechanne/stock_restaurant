# Lotus Garden — Stock Restaurant

Application Flask de gestion des stocks pour le restaurant **Lotus Garden** :
cuisine (ingrédients, recettes, ventes, transferts) et bar (boissons, sessions de caisse, pointage).

---

## Fonctionnalités

### Cuisine
- **Ingrédients** — ajout, modification, suppression ; stock magasin & stock cuisine séparés
- **Seuil d’alerte** — badge rouge dans la navbar + section dédiée sur le dashboard quand `stock_cuisine < seuil_alerte`
- **Recettes (fiches techniques)** — création, modification, duplication, suppression ; ingrédients avec quantités
- **Ventes** — enregistrement d’une vente → décrémentation automatique du stock cuisine
- **Entrées cuisine (transferts)** — transfert magasin → cuisine ou cuisine → magasin, historique paginé (20/page)

### Bar / Caisse
- **Boissons** — catalogue (nom, unité, prix unitaire)
- **Sessions de caisse** — ouverture/fermeture par caissier, historique paginé (20/page)
- **Pointage par boisson** — `Stock initial + Entrées − Stock final = Vendu`
- **Livraisons bar** — enregistrement des entrées boissons, historique paginé (20/page)

### Tableau de bord
- KPIs : nombre d’ingrédients, nombre de recettes, total stock cuisine
- **Alertes stock** en rouge (ingrédients dont `stock_cuisine < seuil_alerte`)
- Graphiques **Top plats** et **Top boissons** sur période filtrée (date + heure)
- Détails des ventes cuisine et transferts sur la période (accordión)
- Exports **CSV** cuisine et bar
- Exports **PDF** (point cuisine sur période, rapport journalier)

### Authentification
- Connexion obligatoire (Flask-Login) — toutes les routes sont protégées (`@login_required`)
- Compte unique admin ; mot de passe stocké hashé (Werkzeug `pbkdf2`)
- Lien de déconnexion dans la navbar de toutes les pages

---

## Stack technique

| Composant | Version |
|-----------|---------|
| Python | 3.10+ |
| Flask | 3.1.0 |
| Flask-SQLAlchemy | 3.1.1 |
| Flask-Migrate (Alembic) | 4.1.0 |
| Flask-Login | 0.6.3 |
| Werkzeug | 3.1.3 |
| WeasyPrint | 65.1 |
| python-dotenv | 1.2.1 |
| SQLite | fichier `stock.db` |

---

## Installation

### 1. Cloner & créer l’environnement

```bash
git clone <repo>
cd stock_restaurant

python -m venv .venv
source .venv/bin/activate        # Linux / Mac
.venv\Scripts\activate          # Windows cmd
.venv\Scripts\Activate.ps1      # Windows PowerShell

pip install -r requirements.txt
```

### 2. Variables d’environnement

Créer un fichier `.env` à la racine :

```env
FLASK_APP=app.py
SECRET_KEY=changez-moi-en-production
ADMIN_PASSWORD=votre_mot_de_passe
```

> `ADMIN_PASSWORD` est utilisé **une seule fois** au premier démarrage pour créer le compte `admin`.
> Si la table `user` n’est pas vide, ce bloc est ignoré.

### 3. Initialiser la base de données

```bash
flask db upgrade
```

### 4. Lancer en développement

```bash
flask run
```

Application accessible sur <http://127.0.0.1:5000>.

---

## Connexion

| Champ | Valeur |
|-------|--------|
| Username | `admin` |
| Password | défini par `ADMIN_PASSWORD` dans `.env` |

Pour modifier le mot de passe d’un compte existant :

```bash
flask shell
>>> from app import db, User
>>> u = User.query.filter_by(username='admin').first()
>>> u.set_password('nouveau_mdp')
>>> db.session.commit()
```

---

## Migrations (Alembic)

Les tables sont gérées exclusivement via Flask-Migrate. Ne pas utiliser `db.create_all()`.

```bash
# Générer une migration après modification d’un modèle
flask db migrate -m "description"

# Appliquer les migrations en attente
flask db upgrade

# Voir la révision courante
flask db current
```

---

## Déploiement (production)

```bash
gunicorn -w 2 -b 0.0.0.0:8000 app:app
```

Configurer un proxy inverse (nginx, Caddy…) devant gunicorn.
Définir `SECRET_KEY` avec une valeur longue et aléatoire.

---

## Structure du projet

```
stock_restaurant/
├── app.py                  # Application Flask (modèles, routes)
├── requirements.txt        # Dépendances Python (UTF-8)
├── stock.db                # Base SQLite (non versionnée)
├── .env                    # Variables d’environnement (non versionné)
├── migrations/             # Scripts Alembic
│   └── versions/
├── static/
│   └── logo.png
└── templates/
    ├── login.html
    ├── home.html           # Dashboard (KPIs, alertes, graphiques)
    ├── ajouter.html        # Gestion ingrédients + seuils d’alerte
    ├── recettes.html       # Fiches techniques
    ├── modifier_recette.html
    ├── ventes.html
    ├── transfert.html      # Entrées cuisine (paginé)
    ├── bar.html            # Caisse bar (paginé)
    └── entrees.html        # Livraisons bar (paginé)
```

---

## Licence

MIT — © 2025 Lotus Garden Stock Manager by Melvina MIGAN
