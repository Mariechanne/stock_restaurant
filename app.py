import csv
import io
import os
from datetime import datetime, timedelta
from flask import Flask, Response, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
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

# Modèles
class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    unite = db.Column(db.String(50), nullable=False)
    stock_cuisine = db.Column(db.Float, nullable=False, default=0.0)
    stock_magasin = db.Column(db.Float, nullable=False, default=0.0)

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

class Transfert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.id'), nullable=False)
    quantite = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    ingredient = db.relationship('Ingredient')

class HistoriqueTransfert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ingredient_id = db.Column(db.Integer, db.ForeignKey('ingredient.id'), nullable=False)
    quantite = db.Column(db.Float, nullable=False)
    unite = db.Column(db.String(50), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    sens = db.Column(db.String(20), nullable=False)
    ingredient = db.relationship('Ingredient', backref='transferts')

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    date_to = request.args.get('date_to', datetime.utcnow().date().isoformat())
    date_from = request.args.get('date_from', (datetime.fromisoformat(date_to) - timedelta(days=30)).date().isoformat())
    
    # Heure de début et fin, par défaut : toute la journée
    heure_debut = request.args.get('heure_debut', '00:00')
    heure_fin = request.args.get('heure_fin', '23:59')

    dt_from = datetime.fromisoformat(date_from + ' ' + heure_debut)
    dt_to = datetime.fromisoformat(date_to + ' ' + heure_fin)

    count_ingredients = Ingredient.query.count()
    count_recettes = Recette.query.count()
    total_stock_cuisine = db.session.query(func.sum(Ingredient.stock_cuisine)).scalar() or 0

    ventes_mois = Vente.query.filter(Vente.date >= dt_from, Vente.date <= dt_to).all()
    transferts_mois = HistoriqueTransfert.query.filter(HistoriqueTransfert.date >= dt_from, HistoriqueTransfert.date <= dt_to).all()

    return render_template('home.html',
        count_ingredients=count_ingredients,
        count_recettes=count_recettes,
        total_stock_cuisine=total_stock_cuisine,
        ventes_mois=ventes_mois,
        transferts_mois=transferts_mois,
        current_time=datetime.utcnow(),
        date_from=date_from,
        date_to=date_to,
        heure_debut=heure_debut,
        heure_fin=heure_fin
    )


@app.route('/rapport/journalier/pdf')
def rapport_journalier_pdf():
    date_str = request.args.get('date', datetime.utcnow().date().isoformat())
    heure_debut = request.args.get('heure_debut', '00:00')
    heure_fin = request.args.get('heure_fin', '23:59')

    # Fusion date + heure
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
def ajouter():
    if request.method == 'POST':
        try:
            nom = request.form['nom']
            unite = request.form['unite']
            stock_magasin = float(request.form.get('stock_magasin', 0))
            stock_cuisine = float(request.form.get('stock_cuisine', 0))

            nouveau = Ingredient(nom=nom, unite=unite, stock_magasin=stock_magasin, stock_cuisine=stock_cuisine)
            db.session.add(nouveau)
            db.session.commit()
            return redirect(url_for('ajouter_ingredient'), current_time=datetime.utcnow())

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l'ajout : {e}", "error")

    ingredients = Ingredient.query.order_by(Ingredient.nom.asc()).all()
    return render_template('ajouter.html', ingredients=ingredients)

@app.route('/modifier/<int:id>', methods=['POST'])
def modifier(id):
    ingr = Ingredient.query.get_or_404(id)

    # Récupération sécurisée des champs du formulaire
    ingr.nom = request.form.get('nom', ingr.nom)
    ingr.unite = request.form.get('unite', ingr.unite)

    try:
        ingr.stock_cuisine = float(request.form.get('stock_cuisine', ingr.stock_cuisine))
        ingr.stock_magasin = float(request.form.get('stock_magasin', ingr.stock_magasin))
    except ValueError:
        flash("Erreur : les valeurs de stock doivent être numériques.", "danger")
        return redirect(url_for('ajouter'))

    db.session.commit()
    flash("Ingrédient mis à jour avec succès !", "success")
    return redirect(url_for('ajouter'))

@app.route('/supprimer/<int:id>', methods=['POST'])
def supprimer(id):
    ingr = Ingredient.query.get_or_404(id)
    db.session.delete(ingr)
    db.session.commit()
    return redirect(url_for('ajouter'))

@app.route('/recettes', methods=['GET', 'POST'])
def recettes():
    if request.method == 'POST':
        nom = request.form['nom']
        recette = Recette(nom=nom)
        db.session.add(recette)
        db.session.commit()

        ingredients_ids = request.form.getlist('ingredient_id')
        quantites = request.form.getlist('quantite')

        for i in range(len(ingredients_ids)):
            qtés = quantites[i]
            if qtés.strip():
                db.session.add(RecetteIngredient(recette_id=recette.id, ingredient_id=int(ingredients_ids[i]), quantite=float(qtés)))
        db.session.commit()
        return redirect(url_for('recettes'))

    return render_template('recettes.html', ingredients = Ingredient.query.order_by(Ingredient.nom.asc()).all(), recettes=Recette.query.all())

@app.route('/modifier_recette/<int:id>', methods=['GET', 'POST'])
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
def supprimer_recette(id):
    recette = Recette.query.get_or_404(id)
    db.session.delete(recette)
    db.session.commit()
    return redirect(url_for('recettes'))

@app.route('/recette/dupliquer/<int:id>', methods=['POST'])
def dupliquer_recette(id):
    recette_originale = Recette.query.get_or_404(id)
    
    # Nouveau nom basé sur l'original
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
def transfert():
    ingredients = Ingredient.query.order_by(Ingredient.nom.asc()).all()
    transferts = HistoriqueTransfert.query.order_by(HistoriqueTransfert.date.desc()).all()

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
