from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from flask_migrate import Migrate


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret") # nécessaire pour flash()

# Configuration de la base de données SQLite
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'stock.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Modèle d'Ingrédient
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
    sens = db.Column(db.String(20), nullable=False)  # <-- ce champ doit exister


with app.app_context():
    db.create_all()

@app.route('/')
def home():
    ingredients = Ingredient.query.all()
    return render_template('index.html', ingredients=ingredients)

@app.route('/ajouter', methods=['POST'])
def ajouter():
    nom = request.form['nom']
    unite = request.form['unite']
    stock_magasin = float(request.form.get('stock_magasin', 0))
    stock_cuisine = float(request.form.get('stock_cuisine', 0))
    nouveau = Ingredient(nom=nom, unite=unite, stock_magasin=stock_magasin, stock_cuisine=stock_cuisine)
    db.session.add(nouveau)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/modifier/<int:id>', methods=['POST'])
def modifier(id):
    ingr = Ingredient.query.get_or_404(id)
    ingr.stock_cuisine = float(request.form.get('stock_cuisine', ingr.stock_cuisine))
    ingr.stock_magasin = float(request.form.get('stock_magasin', ingr.stock_magasin))
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/supprimer/<int:id>', methods=['POST'])
def supprimer(id):
    ingr = Ingredient.query.get_or_404(id)
    db.session.delete(ingr)
    db.session.commit()
    return redirect(url_for('home'))

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
            ingr_id = ingredients_ids[i]
            qtés = quantites[i]

            if qtés.strip() != "":
                ri = RecetteIngredient(
                    recette_id=recette.id,
                    ingredient_id=int(ingr_id),
                    quantite=float(qtés)
                )
                db.session.add(ri)

        db.session.commit()
        return redirect(url_for('recettes'))

    all_ingredients = Ingredient.query.all()
    all_recettes = Recette.query.all()
    return render_template('recettes.html', ingredients=all_ingredients, recettes=all_recettes)

@app.route('/modifier_recette/<int:id>', methods=['GET', 'POST'])
def modifier_recette(id):
    recette = Recette.query.get_or_404(id)
    ingredients = Ingredient.query.all()

    if request.method == 'POST':
        recette.nom = request.form['nom']
        RecetteIngredient.query.filter_by(recette_id=recette.id).delete()

        nouveaux_ingredients = request.form.getlist('ingredient_id')
        for ingr_id in nouveaux_ingredients:
            qty_str = request.form.get(f'quantite_{ingr_id}', '0')
            try:
                qty = float(qty_str)
                if qty > 0:
                    ri = RecetteIngredient(
                        recette_id=recette.id,
                        ingredient_id=int(ingr_id),
                        quantite=qty
                    )
                    db.session.add(ri)
            except ValueError:
                continue

        db.session.commit()
        return redirect(url_for('recettes'))

    quantites = {ri.ingredient_id: ri.quantite for ri in recette.ingredients}
    return render_template('modifier_recette.html', recette=recette, ingredients=ingredients, quantites=quantites)

@app.route('/recette/supprimer/<int:id>', methods=['POST'])
def supprimer_recette(id):
    recette = Recette.query.get_or_404(id)
    db.session.delete(recette)
    db.session.commit()
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
            stock_suffisant = True
            for item in recette.ingredients:
                ingredient = item.ingredient
                quantite_totale = item.quantite * quantite_vendue
                if ingredient.stock_cuisine < quantite_totale:
                    stock_suffisant = False
                    break

            if stock_suffisant:
                vente = Vente(recette_id=recette.id, quantite=quantite_vendue)
                db.session.add(vente)

                for item in recette.ingredients:
                    ingredient = item.ingredient
                    ingredient.stock_cuisine -= item.quantite * quantite_vendue

                db.session.commit()
                message = "✅ Vente enregistrée avec succès."
            else:
                message = "❌ Stock insuffisant pour cette recette."

    return render_template('ventes.html', recettes=recettes, message=message)

@app.route('/transfert', methods=['GET', 'POST'])
def transfert():
    ingredients = Ingredient.query.all()
    transferts = HistoriqueTransfert.query.order_by(HistoriqueTransfert.date.desc()).all()

    if request.method == 'POST':
        try:
            ingredient_id = int(request.form['ingredient'])
            quantite = float(request.form['quantite'])
            sens = request.form['sens']

            ingredient = Ingredient.query.get(ingredient_id)
            if not ingredient:
                flash("Ingrédient introuvable", "error")
                return redirect(url_for('transfert'))

            if sens == 'magasin_vers_cuisine':
                if ingredient.stock_magasin < quantite:
                    flash("Stock magasin insuffisant", "error")
                    return redirect(url_for('transfert'))
                ingredient.stock_magasin -= quantite
                ingredient.stock_cuisine += quantite

            elif sens == 'cuisine_vers_magasin':
                if ingredient.stock_cuisine < quantite:
                    flash("Stock cuisine insuffisant", "error")
                    return redirect(url_for('transfert'))
                ingredient.stock_cuisine -= quantite
                ingredient.stock_magasin += quantite
            else:
                flash("Sens de transfert inconnu", "error")
                return redirect(url_for('transfert'))

            historique = HistoriqueTransfert(
                ingredient_id=ingredient.id,
                quantite=quantite,
                unite=ingredient.unite,
                sens=sens,
                date=datetime.utcnow()
            )

            db.session.add(historique)
            db.session.commit()
            flash("Transfert effectué avec succès", "success")
            return redirect(url_for('transfert'))

        except Exception as e:
            flash(f"Erreur : {str(e)}", "error")

    return render_template('transfert.html', ingredients=ingredients, transferts=transferts)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

