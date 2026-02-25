import csv
import io
import os
from datetime import datetime, timedelta
from flask import Flask, Response, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from flask import make_response
from xhtml2pdf import pisa

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret")  # nécessaire pour flash()

# Configuration de la base de données SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'stock.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialisation
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = "Veuillez vous connecter pour accéder à cette page."
login_manager.login_message_category = "warning"

# ========================
#        MODÈLES
# ========================

class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    unite = db.Column(db.String(50), nullable=False)
    stock_cuisine = db.Column(db.Float, nullable=False, default=0.0)
    stock_magasin = db.Column(db.Float, nullable=False, default=0.0)
    seuil_alerte = db.Column(db.Float, nullable=True, default=None)

class Recette(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    ingredients = db.relationship('RecetteIngredient', backref='recette', cascade='all, delete-orphan')

class RecetteIngredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recette_id = db.Column(db.Integer, db.ForeignKey('recette.id'), nullable=False)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.id'), nullable=False)
    quantite = db.Column(db.Float, nullable=False)
    ingredient = db.relationship('Ingredient')

class Vente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recette_id = db.Column(db.Integer, db.ForeignKey('recette.id'), nullable=False)
    quantite = db.Column(db.Integer, nullable=False, default=1)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    recette = db.relationship('Recette')

class HistoriqueTransfert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.id'), nullable=False)
    quantite = db.Column(db.Float, nullable=False)
    unite = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    sens = db.Column(db.String(20), nullable=False)
    ingredient = db.relationship('Ingredient', backref='transferts')

# === GESTION DU BAR ===

class Caissier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)

class Boisson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prix_unitaire = db.Column(db.Float, nullable=False, default=0.0)

# Ventes de boissons (si utilisées ailleurs)
class VenteBoisson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    boisson_id = db.Column(db.Integer, db.ForeignKey('boisson.id'), nullable=False)
    caissier_id = db.Column(db.Integer, db.ForeignKey('caissier.id'), nullable=False)
    quantite = db.Column(db.Float, nullable=False, default=0.0)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    boisson = db.relationship('Boisson')
    caissier = db.relationship('Caissier')

# Sessions de caisse (logique Excel : SI/ACHAT/SF → VENTE × P.U ; Réel vs Attendu)
class SessionCaisse(db.Model):
    __tablename__ = "session_caisse"
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)  # on enregistre la date de fin de période
    caissier_id = db.Column(db.Integer, db.ForeignKey('caissier.id'), nullable=False)
    montant_reel = db.Column(db.Float, nullable=False, default=0.0)
    montant_attendu = db.Column(db.Float, nullable=False, default=0.0)
    ecart = db.Column(db.Float, nullable=False, default=0.0)
    caissier = db.relationship('Caissier')
    lignes = db.relationship('SessionLigne', backref='session', cascade="all, delete-orphan")

class SessionLigne(db.Model):
    __tablename__ = "session_ligne"
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session_caisse.id'), nullable=False)
    boisson_id = db.Column(db.Integer, db.ForeignKey('boisson.id'), nullable=False)

    stock_initial = db.Column(db.Float, nullable=False, default=0.0)  # SI
    entrees = db.Column(db.Float, nullable=False, default=0.0)        # ACHAT (entrées)
    stock_final = db.Column(db.Float, nullable=False, default=0.0)    # SF

    prix_unitaire_snap = db.Column(db.Float, nullable=False, default=0.0)  # P.U “photo”
    boisson = db.relationship('Boisson')

    @property
    def quantite_vendue(self):
        return max(0.0, (self.stock_initial + self.entrees - self.stock_final))

    @property
    def montant_attendu_ligne(self):
        return self.quantite_vendue * self.prix_unitaire_snap

# Entrées (livraisons) quotidiennes de boissons
class EntreeBoisson(db.Model):
    __tablename__ = "entree_boisson"
    id = db.Column(db.Integer, primary_key=True)
    boisson_id = db.Column(db.Integer, db.ForeignKey('boisson.id'), nullable=False)
    quantite = db.Column(db.Float, nullable=False, default=0.0)
    date = db.Column(db.Date, nullable=False)  # date de la livraison/entrée
    note = db.Column(db.String(200), nullable=True)
    boisson = db.relationship('Boisson')

    @staticmethod
    def total_entrees_pour_date(boisson_id: int, date_pointage):
        """Somme des entrées (livraisons) pour une boisson à la date donnée."""
        q = db.session.query(func.coalesce(func.sum(EntreeBoisson.quantite), 0.0))\
            .filter(EntreeBoisson.boisson_id == boisson_id,
                    EntreeBoisson.date == date_pointage)
        return float(q.scalar() or 0.0)

    @staticmethod
    def total_entrees_entre(boisson_id: int, date_debut, date_fin):
        """Somme des entrées entre deux dates (inclusives)."""
        q = db.session.query(func.coalesce(func.sum(EntreeBoisson.quantite), 0.0))\
            .filter(EntreeBoisson.boisson_id == boisson_id,
                    EntreeBoisson.date >= date_debut,
                    EntreeBoisson.date <= date_fin)
        return float(q.scalar() or 0.0)

    @staticmethod
    def dernier_stock_final_avant(boisson_id: int, date_pointage):
        """Récupère le SF le plus récent AVANT cette date (pour chaîner SI)."""
        l = (SessionLigne.query
             .join(SessionCaisse, SessionLigne.session_id == SessionCaisse.id)
             .filter(SessionLigne.boisson_id == boisson_id,
                     SessionCaisse.date < date_pointage)
             .order_by(SessionCaisse.date.desc(), SessionLigne.id.desc())
             .first())
        if l:
            return float(l.stock_final or 0.0)
        return 0.0

# === AUTHENTIFICATION ===

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Les tables sont gérées via Flask-Migrate (Alembic).
# Au premier déploiement, exécuter : flask db upgrade

def _create_admin_if_needed():
    """Crée l'utilisateur admin si aucun User n'existe et que ADMIN_PASSWORD est défini."""
    try:
        if User.query.count() == 0:
            pwd = os.environ.get("ADMIN_PASSWORD")
            if pwd:
                admin = User(username="admin")
                admin.set_password(pwd)
                db.session.add(admin)
                db.session.commit()
    except Exception:
        db.session.rollback()

with app.app_context():
    _create_admin_if_needed()

# ========================
#         ROUTES
# ========================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        flash("Identifiants incorrects.", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for('login'))

@app.route('/bar', methods=['GET', 'POST'])
@login_required
def pointage_bar():
    # Pour formulaires d’ajout & affichage
    boissons = Boisson.query.order_by(Boisson.nom.asc()).all()
    caissiers = Caissier.query.order_by(Caissier.nom.asc()).all()

    if request.method == 'POST':
        # --- Pointage de fin de service (session caisse sur PÉRIODE) ---
        caissier_nom = (request.form.get('caissier') or '').strip()
        montant_reel = request.form.get('montant_reel')

        # Période
        date_debut_str = request.form.get('date_debut')
        date_fin_str   = request.form.get('date_fin')

        if not caissier_nom or not date_debut_str or not date_fin_str or montant_reel in (None, ''):
            flash("Caissier, période (du/au) et montant réel sont requis.", "danger")
            return redirect(url_for('pointage_bar'))

        try:
            montant_reel = float(montant_reel)
        except ValueError:
            flash("Montant réel invalide.", "danger")
            return redirect(url_for('pointage_bar'))

        # Récupérer ou créer le caissier
        caissier = Caissier.query.filter_by(nom=caissier_nom).first()
        if not caissier:
            caissier = Caissier(nom=caissier_nom)
            db.session.add(caissier)
            db.session.flush()

        # Dates 'YYYY-MM-DD' -> date
        try:
            date_debut = datetime.fromisoformat(date_debut_str).date()
            date_fin   = datetime.fromisoformat(date_fin_str).date()
        except Exception:
            flash("Dates invalides.", "danger")
            return redirect(url_for('pointage_bar'))

        if date_debut > date_fin:
            flash("La date de début doit être avant ou égale à la date de fin.", "danger")
            return redirect(url_for('pointage_bar'))

        # On enregistre la session à la date de FIN (clôture de la période)
        session = SessionCaisse(date=date_fin, caissier_id=caissier.id, montant_reel=montant_reel)
        db.session.add(session)
        db.session.flush()

        # Lignes de pointage
        boisson_ids = request.form.getlist('boisson_ids')
        total_attendu = 0.0

        for bid in boisson_ids:
            try:
                bid_int = int(bid)
            except (TypeError, ValueError):
                continue

            # 1) SI auto : dernier SF AVANT le début de période (si non saisi)
            si_raw = request.form.get(f"stock_initial_{bid_int}")
            if si_raw not in (None, ''):
                try:
                    si = float(si_raw)
                except ValueError:
                    si = 0.0
            else:
                si = EntreeBoisson.dernier_stock_final_avant(bid_int, date_debut)

            # 2) ACHAT auto : somme des entrées sur [date_debut, date_fin] si non saisi
            ach_raw = request.form.get(f"entrees_{bid_int}")
            if ach_raw not in (None, ''):
                try:
                    ach = float(ach_raw)
                except ValueError:
                    ach = 0.0
            else:
                ach = EntreeBoisson.total_entrees_entre(bid_int, date_debut, date_fin)

            # 3) SF : tel que saisi (sinon 0) — SF à la CLÔTURE de période
            sf_raw = request.form.get(f"stock_final_{bid_int}")
            try:
                sf = float(sf_raw) if (sf_raw not in (None, '',)) else 0.0
            except ValueError:
                sf = 0.0

            boisson = Boisson.query.get(bid_int)
            prix_snap = boisson.prix_unitaire if boisson else 0.0

            ligne = SessionLigne(
                session_id=session.id,
                boisson_id=bid_int,
                stock_initial=si,
                entrees=ach,
                stock_final=sf,
                prix_unitaire_snap=prix_snap
            )
            db.session.add(ligne)
            total_attendu += ligne.montant_attendu_ligne

        session.montant_attendu = total_attendu
        session.ecart = session.montant_reel - total_attendu

        db.session.commit()
        flash(
            f"Pointage enregistré (période {date_debut} → {date_fin}). "
            f"Attendu: {session.montant_attendu:.0f} F | "
            f"Réel: {session.montant_reel:.0f} F | "
            f"Écart: {session.ecart:.0f} F",
            "success"
        )
        return redirect(url_for('pointage_bar'))

    # ------- GET : filtres & rendu -------
    # Filtres pour l’ancien tableau “ventes filtrées” (si encore utilisé)
    caissier_id = request.args.get('caissier_id', type=int)
    date_debut = request.args.get('date_debut', default=str(datetime.utcnow().date()))
    date_fin = request.args.get('date_fin', default=str(datetime.utcnow().date()))

    debut = datetime.fromisoformat(date_debut + ' 00:00')
    fin = datetime.fromisoformat(date_fin + ' 23:59')

    requete = VenteBoisson.query.filter(VenteBoisson.date >= debut, VenteBoisson.date <= fin)
    if caissier_id:
        requete = requete.filter(VenteBoisson.caissier_id == caissier_id)
    ventes_filtrees = requete.all()

    # Historique des sessions (bar)
    page_sessions = request.args.get('page_sessions', 1, type=int)
    sessions = SessionCaisse.query.order_by(SessionCaisse.date.desc()).paginate(page=page_sessions, per_page=20, error_out=False)

    return render_template(
        'bar.html',
        boissons=boissons,
        caissiers=caissiers,
        ventes=ventes_filtrees,
        caissier_id=caissier_id,
        date_debut=date_debut,
        date_fin=date_fin,
        sessions=sessions
    )

# --- CRUD boissons (bar) ---
@app.route('/bar/boisson', methods=['POST'])
@login_required
def ajouter_boisson():
    nom = request.form['nom']
    prix = float(request.form['prix'])
    boisson = Boisson(nom=nom, prix_unitaire=prix)
    db.session.add(boisson)
    db.session.commit()
    return redirect(url_for('pointage_bar'))

@app.route('/bar/boisson/modifier/<int:id>', methods=['POST'])
@login_required
def modifier_boisson(id):
    boisson = Boisson.query.get_or_404(id)
    boisson.nom = request.form['nom']
    boisson.prix_unitaire = float(request.form['prix_unitaire'])
    db.session.commit()
    return redirect(url_for('pointage_bar'))

@app.route('/bar/boisson/supprimer/<int:id>', methods=['POST'])
@login_required
def supprimer_boisson(id):
    boisson = Boisson.query.get_or_404(id)
    db.session.delete(boisson)
    db.session.commit()
    return redirect(url_for('pointage_bar'))

# --- NOUVELLE PAGE : Livraisons / Entrées de boissons ---
@app.route('/bar/entrees', methods=['GET', 'POST'])
@login_required
def entrees_boissons():
    boissons = Boisson.query.order_by(Boisson.nom.asc()).all()

    # --- Enregistrement d'une livraison ---
    if request.method == 'POST':
        date_str = request.form.get('date')
        boisson_id = request.form.get('boisson_id', type=int)
        quantite = request.form.get('quantite')
        note = (request.form.get('note') or '').strip()

        if not date_str or not boisson_id or quantite in (None, ''):
            flash("Date, boisson et quantité sont requis.", "danger")
            return redirect(url_for('entrees_boissons'))

        try:
            qte = float(quantite)
        except ValueError:
            flash("Quantité invalide.", "danger")
            return redirect(url_for('entrees_boissons'))

        try:
            date_liv = datetime.fromisoformat(date_str).date()
        except Exception:
            flash("Date invalide.", "danger")
            return redirect(url_for('entrees_boissons'))

        db.session.add(EntreeBoisson(
            boisson_id=boisson_id,
            quantite=qte,
            date=date_liv,
            note=note
        ))
        db.session.commit()
        flash("Entrée enregistrée.", "success")
        return redirect(url_for('entrees_boissons'))

    # --- Filtres GET ---
    boisson_id_f = request.args.get('boisson_id', type=int)
    date_debut_str = request.args.get('date_debut', '')
    date_fin_str   = request.args.get('date_fin', '')

    # Construire requête filtrée
    q = EntreeBoisson.query

    # Période
    try:
        if date_debut_str:
            d_deb = datetime.fromisoformat(date_debut_str).date()
            q = q.filter(EntreeBoisson.date >= d_deb)
    except Exception:
        flash("Date de début invalide.", "warning")

    try:
        if date_fin_str:
            d_fin = datetime.fromisoformat(date_fin_str).date()
            q = q.filter(EntreeBoisson.date <= d_fin)
    except Exception:
        flash("Date de fin invalide.", "warning")

    # Boisson
    if boisson_id_f:
        q = q.filter(EntreeBoisson.boisson_id == boisson_id_f)

    # Résultats
    q = q.order_by(EntreeBoisson.date.desc(), EntreeBoisson.id.desc())
    page = request.args.get('page', 1, type=int)
    recent = q.paginate(page=page, per_page=20, error_out=False)

    # Total filtré
    total_filtre = (db.session.query(func.coalesce(func.sum(EntreeBoisson.quantite), 0.0))
                    .filter(*(q._criterion,) if getattr(q, "_criterion", None) is not None else [])
                    .scalar() if getattr(q, "_criterion", None) is not None else
                    db.session.query(func.coalesce(func.sum(EntreeBoisson.quantite), 0.0)).scalar())
    total_filtre = float(total_filtre or 0.0)

    return render_template(
        'entrees.html',
        boissons=boissons,
        recent=recent,
        boisson_id_f=boisson_id_f,
        date_debut=date_debut_str,
        date_fin=date_fin_str,
        total_filtre=total_filtre
    )

# --- Accueil / Rapports / Cuisine ---

from flask import make_response  # déjà importé chez toi

@app.route('/')
@login_required
def home():
    # Période par défaut : les 30 derniers jours, journée entière
    date_to = request.args.get('date_to', datetime.utcnow().date().isoformat())
    date_from = request.args.get(
        'date_from',
        (datetime.fromisoformat(date_to) - timedelta(days=30)).date().isoformat()
    )
    heure_debut = request.args.get('heure_debut', '00:00')
    heure_fin = request.args.get('heure_fin', '23:59')

    # Fenêtre temporelle pour VENTES (cuisine) : datetimes
    dt_from = datetime.fromisoformat(f"{date_from} {heure_debut}")
    dt_to   = datetime.fromisoformat(f"{date_to} {heure_fin}")

    # ---- KPIs globaux (existant) ----
    count_ingredients = Ingredient.query.count()
    count_recettes = Recette.query.count()
    total_stock_cuisine = db.session.query(func.sum(Ingredient.stock_cuisine)).scalar() or 0

    # ---- Vue CUISINE : top plats vendus (quantités) ----
    # SUM(Vente.quantite) groupé par recette dans la fenêtre [dt_from, dt_to]
    top_recettes = (
        db.session.query(
            Recette.nom.label('recette'),
            func.coalesce(func.sum(Vente.quantite), 0).label('qte')
        )
        .join(Recette, Recette.id == Vente.recette_id)
        .filter(Vente.date >= dt_from, Vente.date <= dt_to)
        .group_by(Recette.nom)
        .order_by(func.coalesce(func.sum(Vente.quantite), 0).desc())
        .all()
    )
    # Transforme en listes simples pour le graph/table
    recettes_labels = [r.recette for r in top_recettes]
    recettes_qtes = [float(r.qte or 0) for r in top_recettes]

    # ---- Vue CAISSE (BAR) : top boissons vendues ----
    # On somme (SI + ACHAT - SF) par boisson sur la période, côté SessionCaisse.date
    top_boissons = (
        db.session.query(
            Boisson.nom.label('boisson'),
            func.coalesce(func.sum(SessionLigne.stock_initial + SessionLigne.entrees - SessionLigne.stock_final), 0).label('qte_vendue'),
            func.coalesce(func.sum((SessionLigne.stock_initial + SessionLigne.entrees - SessionLigne.stock_final) * SessionLigne.prix_unitaire_snap), 0).label('montant')
        )
        .join(SessionCaisse, SessionCaisse.id == SessionLigne.session_id)
        .join(Boisson, Boisson.id == SessionLigne.boisson_id)
        .filter(SessionCaisse.date >= datetime.fromisoformat(date_from).date(),
                SessionCaisse.date <= datetime.fromisoformat(date_to).date())
        .group_by(Boisson.nom)
        .order_by(func.coalesce(func.sum(SessionLigne.stock_initial + SessionLigne.entrees - SessionLigne.stock_final), 0).desc())
        .all()
    )
    boissons_labels = [b.boisson for b in top_boissons]
    boissons_qtes = [float(b.qte_vendue or 0) for b in top_boissons]

    # Données existantes si tu veux les réutiliser dans la page
    ventes_mois = Vente.query.filter(Vente.date >= dt_from, Vente.date <= dt_to).all()
    transferts_mois = HistoriqueTransfert.query.filter(HistoriqueTransfert.date >= dt_from, HistoriqueTransfert.date <= dt_to).all()

    # Alertes stock : ingrédients sous leur seuil d'alerte
    alertes = Ingredient.query.filter(
        Ingredient.seuil_alerte.isnot(None),
        Ingredient.stock_cuisine < Ingredient.seuil_alerte
    ).order_by(Ingredient.nom.asc()).all()

    return render_template(
        'home.html',
        # Filtres
        date_from=date_from, date_to=date_to,
        heure_debut=heure_debut, heure_fin=heure_fin,
        # KPIs globaux
        count_ingredients=count_ingredients,
        count_recettes=count_recettes,
        total_stock_cuisine=total_stock_cuisine,
        # Cuisine (plats)
        recettes_labels=recettes_labels,
        recettes_qtes=recettes_qtes,
        top_recettes=top_recettes,
        # Bar (boissons)
        boissons_labels=boissons_labels,
        boissons_qtes=boissons_qtes,
        top_boissons=top_boissons,
        # Données brutes (si besoin ailleurs)
        ventes_mois=ventes_mois,
        transferts_mois=transferts_mois,
        current_time=datetime.utcnow(),
        # Alertes stock
        alertes=alertes
    )


@app.route('/export/cuisine.csv')
@login_required
def export_cuisine_csv():
    """Export CSV du point Cuisine (ventes par recette) sur une période."""
    date_to = request.args.get('date_to', datetime.utcnow().date().isoformat())
    date_from = request.args.get(
        'date_from',
        (datetime.fromisoformat(date_to) - timedelta(days=30)).date().isoformat()
    )
    heure_debut = request.args.get('heure_debut', '00:00')
    heure_fin = request.args.get('heure_fin', '23:59')

    dt_from = datetime.fromisoformat(f"{date_from} {heure_debut}")
    dt_to   = datetime.fromisoformat(f"{date_to} {heure_fin}")

    rows = (
        db.session.query(
            Recette.nom.label('recette'),
            func.coalesce(func.sum(Vente.quantite), 0).label('quantite')
        )
        .join(Recette, Recette.id == Vente.recette_id)
        .filter(Vente.date >= dt_from, Vente.date <= dt_to)
        .group_by(Recette.nom)
        .order_by(func.coalesce(func.sum(Vente.quantite), 0).desc())
        .all()
    )

    # Génération CSV en mémoire
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Recette", "Quantité vendue", "Période", "Heure début", "Heure fin"])
    for r in rows:
        writer.writerow([r.recette, int(r.quantite or 0), f"{date_from} -> {date_to}", heure_debut, heure_fin])

    resp = make_response(output.getvalue())
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = f"attachment; filename=point_cuisine_{date_from}_to_{date_to}.csv"
    return resp

@app.route('/export/bar.csv')
@login_required
def export_bar_csv():
    """
    Export CSV des boissons les plus vendues sur une période.
    Basé sur les sessions de caisse : somme (SI + ACHAT - SF) par boisson.
    """
    date_to = request.args.get('date_to', datetime.utcnow().date().isoformat())
    date_from = request.args.get(
        'date_from',
        (datetime.fromisoformat(date_to) - timedelta(days=30)).date().isoformat()
    )

    # Agrégat sur SessionCaisse.date (par jour de clôture de période)
    rows = (
        db.session.query(
            Boisson.nom.label('boisson'),
            func.coalesce(func.sum(SessionLigne.stock_initial + SessionLigne.entrees - SessionLigne.stock_final), 0).label('quantite'),
            func.coalesce(func.sum((SessionLigne.stock_initial + SessionLigne.entrees - SessionLigne.stock_final) * SessionLigne.prix_unitaire_snap), 0).label('montant')
        )
        .join(SessionCaisse, SessionCaisse.id == SessionLigne.session_id)
        .join(Boisson, Boisson.id == SessionLigne.boisson_id)
        .filter(SessionCaisse.date >= datetime.fromisoformat(date_from).date(),
                SessionCaisse.date <= datetime.fromisoformat(date_to).date())
        .group_by(Boisson.nom)
        .order_by(func.coalesce(func.sum(SessionLigne.stock_initial + SessionLigne.entrees - SessionLigne.stock_final), 0).desc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Boisson", "Quantité vendue", "Montant (F)", "Période"])
    for r in rows:
        writer.writerow([r.boisson, f"{float(r.quantite or 0):.2f}", f"{float(r.montant or 0):.2f}", f"{date_from} -> {date_to}"])

    resp = make_response(output.getvalue())
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = f"attachment; filename=point_boissons_{date_from}_to_{date_to}.csv"
    return resp


@app.route('/rapport/cuisine_periode/pdf')
@login_required
def rapport_cuisine_periode_pdf():
    """
    PDF 'Point Cuisine – Période' : mêmes données que le journalier,
    mais sur [date_from, date_to] avec heures.
    Le nom de fichier reflète la période.
    """
    date_to = request.args.get('date_to', datetime.utcnow().date().isoformat())
    date_from = request.args.get(
        'date_from',
        (datetime.fromisoformat(date_to) - timedelta(days=30)).date().isoformat()
    )
    heure_debut = request.args.get('heure_debut', '00:00')
    heure_fin = request.args.get('heure_fin', '23:59')

    dt_debut = datetime.fromisoformat(f"{date_from} {heure_debut}")
    dt_fin   = datetime.fromisoformat(f"{date_to} {heure_fin}")

    ventes = Vente.query.filter(Vente.date >= dt_debut, Vente.date <= dt_fin).all()
    transferts = HistoriqueTransfert.query.filter(HistoriqueTransfert.date >= dt_debut, HistoriqueTransfert.date <= dt_fin).all()
    ingredients = Ingredient.query.order_by(Ingredient.nom.asc()).all()

    # On réutilise le template existant 'rapport_pdf.html'
    # en passant un 'date' lisible (plage)
    html = render_template(
        'rapport_pdf.html',
        date=f"{date_from} → {date_to}",
        heure_debut=heure_debut,
        heure_fin=heure_fin,
        ventes=ventes,
        transferts=transferts,
        ingredients=ingredients
    )

    result = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(html), dest=result)
    if pisa_status.err:
        return f"Erreur de génération PDF : {pisa_status.err}", 500

    fname = f"point_cuisine_{date_from}_{heure_debut.replace(':','')}_to_{date_to}_{heure_fin.replace(':','')}.pdf"
    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename={fname}'
    return response

@app.route('/rapport/journalier/pdf')
@login_required
def rapport_journalier_pdf():
    date_str = request.args.get('date', datetime.utcnow().date().isoformat())
    heure_debut = request.args.get('heure_debut', '00:00')
    heure_fin = request.args.get('heure_fin', '23:59')

    dt_debut = datetime.fromisoformat(f"{date_str} {heure_debut}")
    dt_fin = datetime.fromisoformat(f"{date_str} {heure_fin}")

    ventes = Vente.query.filter(Vente.date >= dt_debut, Vente.date <= dt_fin).all()
    transferts = HistoriqueTransfert.query.filter(HistoriqueTransfert.date >= dt_debut, HistoriqueTransfert.date <= dt_fin).all()
    ingredients = Ingredient.query.order_by(Ingredient.nom.asc()).all()

    html = render_template(
        'rapport_pdf.html',
        date=date_str,
        heure_debut=heure_debut,
        heure_fin=heure_fin,
        ventes=ventes,
        transferts=transferts,
        ingredients=ingredients
    )

    result = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(html), dest=result)

    if pisa_status.err:
        return f"Erreur de génération PDF : {pisa_status.err}", 500

    response = make_response(result.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=rapport_{date_str}_{heure_debut}_{heure_fin}.pdf'
    return response

@app.route('/ajouter', methods=['GET', 'POST'])
@login_required
def ajouter():
    if request.method == 'POST':
        try:
            nom = request.form['nom']
            unite = request.form['unite']
            stock_magasin = float(request.form.get('stock_magasin', 0))
            stock_cuisine = float(request.form.get('stock_cuisine', 0))
            seuil_raw = request.form.get('seuil_alerte', '').strip()
            seuil_alerte = float(seuil_raw) if seuil_raw else None

            nouveau = Ingredient(nom=nom, unite=unite, stock_magasin=stock_magasin, stock_cuisine=stock_cuisine, seuil_alerte=seuil_alerte)
            db.session.add(nouveau)
            db.session.commit()
            return redirect(url_for('ajouter'), current_time=datetime.utcnow())

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'ajout : {e}", "error")

    ingredients = Ingredient.query.order_by(Ingredient.nom.asc()).all()
    return render_template('ajouter.html', ingredients=ingredients)

@app.route('/modifier/<int:id>', methods=['POST'])
@login_required
def modifier(id):
    ingr = Ingredient.query.get_or_404(id)

    ingr.nom = request.form.get('nom', ingr.nom)
    ingr.unite = request.form.get('unite', ingr.unite)

    try:
        ingr.stock_cuisine = float(request.form.get('stock_cuisine', ingr.stock_cuisine))
        ingr.stock_magasin = float(request.form.get('stock_magasin', ingr.stock_magasin))
        seuil_raw = request.form.get('seuil_alerte', '').strip()
        ingr.seuil_alerte = float(seuil_raw) if seuil_raw else None
    except ValueError:
        flash("Erreur : les valeurs de stock doivent être numériques.", "danger")
        return redirect(url_for('ajouter'))

    db.session.commit()
    flash("Ingrédient mis à jour avec succès !", "success")
    return redirect(url_for('ajouter'))

@app.route('/supprimer/<int:id>', methods=['POST'])
@login_required
def supprimer(id):
    ingr = Ingredient.query.get_or_404(id)
    db.session.delete(ingr)
    db.session.commit()
    return redirect(url_for('ajouter'))

@app.route('/recettes', methods=['GET', 'POST'])
@login_required
def recettes():
    if request.method == 'POST':
        nom = request.form['nom']
        recette = Recette(nom=nom)
        db.session.add(recette)
        db.session.commit()

        ingredients_ids = request.form.getlist('ingredient_id')
        quantites = request.form.getlist('quantite')

        for i in range(len(ingredients_ids)):
            qtes = quantites[i]
            if qtes.strip():
                db.session.add(RecetteIngredient(recette_id=recette.id, ingredient_id=int(ingredients_ids[i]), quantite=float(qtes)))
        db.session.commit()
        return redirect(url_for('recettes'))

    return render_template('recettes.html', ingredients = Ingredient.query.order_by(Ingredient.nom.asc()).all(), recettes=Recette.query.all())

@app.route('/modifier_recette/<int:id>', methods=['GET', 'POST'])
@login_required
def modifier_recette(id):
    recette = Recette.query.get_or_404(id)
    if request.method == 'POST':
        recette.nom = request.form['nom']
        RecetteIngredient.query.filter_by(recette_id=recette.id).delete()

        for ingr_id in request.form.getlist('ingredient_id'):
            qty_str = request.form.get(f'quantite_{ingr_id}', '0')
            try:
                qty = float(qty_str)
                if qty > 0:
                    db.session.add(RecetteIngredient(recette_id=recette.id, ingredient_id=int(ingr_id), quantite=qty))
            except ValueError:
                continue

        db.session.commit()
        return redirect(url_for('recettes'))

    quantites = {ri.ingredient_id: ri.quantite for ri in recette.ingredients}
    return render_template('modifier_recette.html', recette=recette, ingredients = Ingredient.query.order_by(Ingredient.nom.asc()).all(), quantites=quantites)

@app.route('/recette/supprimer/<int:id>', methods=['POST'])
@login_required
def supprimer_recette(id):
    recette = Recette.query.get_or_404(id)
    db.session.delete(recette)
    db.session.commit()
    return redirect(url_for('recettes'))

@app.route('/recette/dupliquer/<int:id>', methods=['POST'])
@login_required
def dupliquer_recette(id):
    recette_originale = Recette.query.get_or_404(id)
    nouveau_nom = f"{recette_originale.nom} (copie)"
    nouvelle_recette = Recette(nom=nouveau_nom)
    db.session.add(nouvelle_recette)
    db.session.flush()  # Pour obtenir l'ID sans commit

    for ingredient_assoc in recette_originale.ingredients:
        copie_ingredient = RecetteIngredient(
            recette_id=nouvelle_recette.id,
            ingredient_id=ingredient_assoc.ingredient_id,
            quantite=ingredient_assoc.quantite
        )
        db.session.add(copie_ingredient)

    db.session.commit()
    flash(f"Recette « {recette_originale.nom} » dupliquée avec succès.", "success")
    return redirect(url_for('recettes'))

@app.route('/ventes', methods=['GET', 'POST'])
@login_required
def ventes():
    recettes = Recette.query.all()
    message = ""

    if request.method == 'POST':
        recette_id = request.form['recette_id']
        quantite_vendue = int(request.form['quantite'])
        recette = Recette.query.get(recette_id)

        if not recette:
            message = "Recette introuvable."
        else:
            stock_suffisant = all(item.ingredient.stock_cuisine >= item.quantite * quantite_vendue for item in recette.ingredients)

            if stock_suffisant:
                db.session.add(Vente(recette_id=recette.id, quantite=quantite_vendue))
                for item in recette.ingredients:
                    item.ingredient.stock_cuisine -= item.quantite * quantite_vendue
                db.session.commit()
                message = "✅ Vente enregistrée avec succès."
            else:
                message = "❌ Stock insuffisant pour cette recette."

    return render_template('ventes.html', recettes=recettes, message=message)

@app.route('/transfert', methods=['GET', 'POST'])
@login_required
def transfert():
    page = request.args.get('page', 1, type=int)
    ingredients = Ingredient.query.order_by(Ingredient.nom.asc()).all()
    transferts = HistoriqueTransfert.query.order_by(HistoriqueTransfert.date.desc()).paginate(page=page, per_page=20, error_out=False)

    if request.method == 'POST':
        try:
            ingredient_id = int(request.form['ingredient'])
            quantite = float(request.form['quantite'])
            sens = request.form['sens']
            ingredient = Ingredient.query.get(ingredient_id)

            if not ingredient:
                flash("Ingrédient introuvable", "error")
            elif sens == 'magasin_vers_cuisine' and ingredient.stock_magasin < quantite:
                flash("Stock magasin insuffisant", "error")
            elif sens == 'cuisine_vers_magasin' and ingredient.stock_cuisine < quantite:
                flash("Stock cuisine insuffisant", "error")
            else:
                if sens == 'magasin_vers_cuisine':
                    ingredient.stock_magasin -= quantite
                    ingredient.stock_cuisine += quantite
                else:
                    ingredient.stock_cuisine -= quantite
                    ingredient.stock_magasin += quantite

                db.session.add(HistoriqueTransfert(
                    ingredient_id=ingredient.id,
                    quantite=quantite,
                    unite=ingredient.unite,
                    sens=sens,
                    date=datetime.utcnow()
                ))
                db.session.commit()
                flash("Transfert effectué avec succès", "success")
                return redirect(url_for('transfert'))
        except Exception as e:
            flash(f"Erreur : {str(e)}", "error")

    return render_template('transfert.html', ingredients=ingredients, transferts=transferts)

@app.context_processor
def inject_request():
    return dict(request=request)

@app.context_processor
def inject_nb_alertes():
    try:
        nb_alertes = Ingredient.query.filter(
            Ingredient.seuil_alerte.isnot(None),
            Ingredient.stock_cuisine < Ingredient.seuil_alerte
        ).count()
    except Exception:
        nb_alertes = 0
    return dict(nb_alertes=nb_alertes, current_time=datetime.utcnow())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
