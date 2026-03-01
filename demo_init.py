#!/usr/bin/env python3
"""
demo_init.py — Initialise la base de données pour le déploiement Render.
Exécuté à chaque démarrage : crée les tables et peuple la DB si elle est vide.
"""
import os, random
from datetime import date, timedelta, datetime
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()
random.seed(2025)

from app import app, db
from app import (User, Ingredient, Recette, RecetteIngredient, Boisson, Caissier,
                  Vente, SessionCaisse, SessionLigne, EntreeBoisson, HistoriqueTransfert)

def seed():
    with app.app_context():
        # Crée les tables si elles n'existent pas
        db.create_all()

        # Idempotent : ne rien faire si déjà peuplé
        if User.query.count() > 0:
            print("DB déjà initialisée, démarrage normal.")
            return

        print("DB vide — initialisation en cours...")

        # ── 1. ADMIN ────────────────────────────────────────────────
        admin = User(username="admin")
        admin.set_password(os.environ.get("ADMIN_PASSWORD", "admin"))
        db.session.add(admin)

        # ── 2. INGRÉDIENTS ──────────────────────────────────────────
        ingredients = [
            Ingredient(id=1,  nom='Riz',                 unite='kg',    stock_magasin=1000.0),
            Ingredient(id=2,  nom='Amanvivè',            unite='Unité', stock_magasin=1000.0),
            Ingredient(id=3,  nom='Tchayo',              unite='Unité', stock_magasin=1000.0),
            Ingredient(id=4,  nom='Goussi',              unite='Unité', stock_magasin=1000.0),
            Ingredient(id=5,  nom='Poisson Fumé',        unite='Unité', stock_magasin=1000.0),
            Ingredient(id=6,  nom='Farine de maïs',      unite='Unité', stock_magasin=1000.0),
            Ingredient(id=7,  nom='Cossette de Manioc',  unite='Unité', stock_magasin=1000.0),
            Ingredient(id=8,  nom='Huile rouge',         unite='L',     stock_magasin=1000.0),
            Ingredient(id=9,  nom="Huile d'arachide",    unite='L',     stock_magasin=1000.0),
            Ingredient(id=11, nom='Banane plantain',     unite='Unité', stock_magasin=1000.0),
            Ingredient(id=12, nom='Fromge',              unite='Unité', stock_magasin=1000.0),
            Ingredient(id=13, nom='Couscous',            unite='Unité', stock_magasin=1000.0),
            Ingredient(id=14, nom='Sardine',             unite='Unité', stock_magasin=1000.0),
            Ingredient(id=15, nom='Œuf',                 unite='Unité', stock_magasin=1000.0),
            Ingredient(id=17, nom='Pâte spaghetti',      unite='Unité', stock_magasin=1000.0),
            Ingredient(id=18, nom='Mayonnaise',          unite='Unité', stock_magasin=1000.0),
            Ingredient(id=19, nom='Viande Spaghettis',   unite='Unité', stock_magasin=1000.0),
            Ingredient(id=20, nom='Viande Shawarma',     unite='Unité', stock_magasin=1000.0),
            Ingredient(id=21, nom='Viande de mouton',    unite='Unité', stock_magasin=1000.0),
            Ingredient(id=22, nom='Pains libannais',     unite='Unité', stock_magasin=1000.0),
            Ingredient(id=23, nom='Viande gbota',        unite='Unité', stock_magasin=1000.0),
            Ingredient(id=24, nom='Asrokouin',           unite='Unité', stock_magasin=1000.0),
            Ingredient(id=25, nom='Crabe',               unite='Unité', stock_magasin=1000.0),
            Ingredient(id=26, nom='Peau',                unite='Unité', stock_magasin=1000.0),
            Ingredient(id=28, nom='Tomate en boîte',     unite='Unité', stock_magasin=1000.0),
            Ingredient(id=29, nom='Poisson sylvie 1000', unite='Unité', stock_magasin=1000.0),
            Ingredient(id=30, nom='Poisson Sylvie 1500', unite='Unité', stock_magasin=1000.0),
            Ingredient(id=31, nom='Poisson Sylvie 2000', unite='Unité', stock_magasin=1000.0),
            Ingredient(id=32, nom='Poisson Sylvie 2000', unite='Unité', stock_magasin=1000.0),
            Ingredient(id=33, nom='Poisson Bar 400g',    unite='Unité', stock_magasin=1000.0),
            Ingredient(id=34, nom='Akassa',              unite='Unité', stock_magasin=1000.0),
            Ingredient(id=35, nom='Gari',                unite='Unité', stock_magasin=1000.0),
            Ingredient(id=36, nom='Boullon',             unite='Unité', stock_magasin=1000.0),
            Ingredient(id=37, nom='Gésier',              unite='Unité', stock_magasin=1000.0),
            Ingredient(id=38, nom='Poulet Bicyclette',   unite='Unité', stock_magasin=1000.0),
            Ingredient(id=39, nom='Coquelet',            unite='Unité', stock_magasin=1000.0),
            Ingredient(id=40, nom='Aileron 1500',        unite='Unité', stock_magasin=1000.0),
            Ingredient(id=41, nom='Aileron 2000',        unite='Unité', stock_magasin=1000.0),
            Ingredient(id=42, nom='Aileron 2500',        unite='Unité', stock_magasin=1000.0),
            Ingredient(id=43, nom='Petit Poids surgelé', unite='Unité', stock_magasin=1000.0),
            Ingredient(id=44, nom='Petit Poids en boîte',unite='Unité', stock_magasin=1000.0),
            Ingredient(id=45, nom='Pomme de terre',      unite='Unité', stock_magasin=1000.0),
            Ingredient(id=46, nom='Laitue',              unite='g',     stock_magasin=1000.0),
            Ingredient(id=48, nom='Concombre',           unite='kg',    stock_magasin=1000.0),
            Ingredient(id=49, nom='Carotte',             unite='kg',    stock_magasin=1000.0),
            Ingredient(id=50, nom='Sauce Shawarma',      unite='L',     stock_magasin=1000.0),
            Ingredient(id=51, nom='Vinaigrette',         unite='L',     stock_magasin=1000.0),
            Ingredient(id=52, nom='Poivron',             unite='g',     stock_magasin=1000.0),
            Ingredient(id=53, nom='Choux',               unite='kg',    stock_magasin=1000.0),
            Ingredient(id=54, nom='Oignon',              unite='kg',    stock_magasin=1000.0),
            Ingredient(id=55, nom='Sel',                 unite='kg',    stock_magasin=1000.0),
            Ingredient(id=56, nom='Spaghettis',          unite='kg',    stock_magasin=1000.0),
            Ingredient(id=57, nom='Frite',               unite='g',     stock_magasin=10000.0),
            Ingredient(id=58, nom='Coquillettes',        unite='g',     stock_magasin=1000.0),
        ]
        db.session.add_all(ingredients)

        # ── 3. RECETTES ─────────────────────────────────────────────
        recettes = [
            Recette(id=1, nom='Légume rouge + pate blanche → 1500'),
            Recette(id=2, nom='Légume rouge + Telibo → 1500'),
            Recette(id=3, nom='Légume Blanc + pate blanche → 1500'),
            Recette(id=4, nom='Légume Blanc + Telibo → 1500'),
            Recette(id=5, nom='Spaghettis Lotus Blanc → 1500'),
            Recette(id=6, nom='Spaghettis Rouge Viande Omelette → 1000'),
            Recette(id=7, nom='Spaghettis Lotus Rouge → 1500'),
            Recette(id=8, nom='Chawarma Lotus → 2500'),
        ]
        db.session.add_all(recettes)

        # ── 4. RECETTE-INGRÉDIENTS ──────────────────────────────────
        ris = [
            # Légume rouge + pate blanche
            RecetteIngredient(recette_id=1, ingredient_id=2,  quantite=1.0),
            RecetteIngredient(recette_id=1, ingredient_id=3,  quantite=1.0),
            RecetteIngredient(recette_id=1, ingredient_id=4,  quantite=1.0),
            RecetteIngredient(recette_id=1, ingredient_id=5,  quantite=1.0),
            RecetteIngredient(recette_id=1, ingredient_id=6,  quantite=1.0),
            RecetteIngredient(recette_id=1, ingredient_id=8,  quantite=0.04),
            RecetteIngredient(recette_id=1, ingredient_id=12, quantite=2.0),
            RecetteIngredient(recette_id=1, ingredient_id=54, quantite=0.1),
            RecetteIngredient(recette_id=1, ingredient_id=55, quantite=0.01),
            # Légume rouge + Telibo
            RecetteIngredient(recette_id=2, ingredient_id=2,  quantite=1.0),
            RecetteIngredient(recette_id=2, ingredient_id=3,  quantite=1.0),
            RecetteIngredient(recette_id=2, ingredient_id=4,  quantite=1.0),
            RecetteIngredient(recette_id=2, ingredient_id=5,  quantite=1.0),
            RecetteIngredient(recette_id=2, ingredient_id=7,  quantite=1.0),
            RecetteIngredient(recette_id=2, ingredient_id=8,  quantite=0.05),
            RecetteIngredient(recette_id=2, ingredient_id=12, quantite=1.0),
            RecetteIngredient(recette_id=2, ingredient_id=54, quantite=0.05),
            RecetteIngredient(recette_id=2, ingredient_id=55, quantite=0.01),
            # Légume Blanc + pate blanche
            RecetteIngredient(recette_id=3, ingredient_id=2,  quantite=1.0),
            RecetteIngredient(recette_id=3, ingredient_id=3,  quantite=1.0),
            RecetteIngredient(recette_id=3, ingredient_id=4,  quantite=1.0),
            RecetteIngredient(recette_id=3, ingredient_id=5,  quantite=1.0),
            RecetteIngredient(recette_id=3, ingredient_id=6,  quantite=1.0),
            RecetteIngredient(recette_id=3, ingredient_id=9,  quantite=0.03),
            RecetteIngredient(recette_id=3, ingredient_id=12, quantite=2.0),
            RecetteIngredient(recette_id=3, ingredient_id=54, quantite=0.1),
            RecetteIngredient(recette_id=3, ingredient_id=55, quantite=0.01),
            # Légume Blanc + Telibo
            RecetteIngredient(recette_id=4, ingredient_id=2,  quantite=1.0),
            RecetteIngredient(recette_id=4, ingredient_id=3,  quantite=1.0),
            RecetteIngredient(recette_id=4, ingredient_id=4,  quantite=1.0),
            RecetteIngredient(recette_id=4, ingredient_id=5,  quantite=1.0),
            RecetteIngredient(recette_id=4, ingredient_id=7,  quantite=1.0),
            RecetteIngredient(recette_id=4, ingredient_id=9,  quantite=0.05),
            RecetteIngredient(recette_id=4, ingredient_id=12, quantite=1.0),
            RecetteIngredient(recette_id=4, ingredient_id=54, quantite=0.05),
            RecetteIngredient(recette_id=4, ingredient_id=55, quantite=0.01),
            # Spaghettis Lotus Blanc
            RecetteIngredient(recette_id=5, ingredient_id=9,  quantite=0.05),
            RecetteIngredient(recette_id=5, ingredient_id=15, quantite=1.0),
            RecetteIngredient(recette_id=5, ingredient_id=19, quantite=1.0),
            RecetteIngredient(recette_id=5, ingredient_id=43, quantite=1.0),
            RecetteIngredient(recette_id=5, ingredient_id=49, quantite=0.05),
            RecetteIngredient(recette_id=5, ingredient_id=52, quantite=0.02),
            RecetteIngredient(recette_id=5, ingredient_id=53, quantite=0.05),
            RecetteIngredient(recette_id=5, ingredient_id=54, quantite=0.05),
            RecetteIngredient(recette_id=5, ingredient_id=55, quantite=0.01),
            RecetteIngredient(recette_id=5, ingredient_id=56, quantite=0.1),
            RecetteIngredient(recette_id=5, ingredient_id=57, quantite=125.0),
            # Spaghettis Rouge Viande Omelette
            RecetteIngredient(recette_id=6, ingredient_id=9,  quantite=0.05),
            RecetteIngredient(recette_id=6, ingredient_id=15, quantite=1.0),
            RecetteIngredient(recette_id=6, ingredient_id=19, quantite=1.0),
            RecetteIngredient(recette_id=6, ingredient_id=28, quantite=0.2),
            RecetteIngredient(recette_id=6, ingredient_id=43, quantite=1.0),
            RecetteIngredient(recette_id=6, ingredient_id=49, quantite=0.05),
            RecetteIngredient(recette_id=6, ingredient_id=52, quantite=0.02),
            RecetteIngredient(recette_id=6, ingredient_id=53, quantite=0.05),
            RecetteIngredient(recette_id=6, ingredient_id=54, quantite=0.05),
            RecetteIngredient(recette_id=6, ingredient_id=55, quantite=0.01),
            RecetteIngredient(recette_id=6, ingredient_id=56, quantite=0.1),
            # Spaghettis Lotus Rouge
            RecetteIngredient(recette_id=7, ingredient_id=9,  quantite=0.05),
            RecetteIngredient(recette_id=7, ingredient_id=15, quantite=1.0),
            RecetteIngredient(recette_id=7, ingredient_id=19, quantite=1.0),
            RecetteIngredient(recette_id=7, ingredient_id=28, quantite=0.2),
            RecetteIngredient(recette_id=7, ingredient_id=43, quantite=1.0),
            RecetteIngredient(recette_id=7, ingredient_id=49, quantite=0.05),
            RecetteIngredient(recette_id=7, ingredient_id=52, quantite=0.02),
            RecetteIngredient(recette_id=7, ingredient_id=53, quantite=0.05),
            RecetteIngredient(recette_id=7, ingredient_id=54, quantite=0.05),
            RecetteIngredient(recette_id=7, ingredient_id=55, quantite=0.01),
            RecetteIngredient(recette_id=7, ingredient_id=56, quantite=0.1),
            RecetteIngredient(recette_id=7, ingredient_id=57, quantite=125.0),
            # Chawarma
            RecetteIngredient(recette_id=8, ingredient_id=20, quantite=1.0),
        ]
        db.session.add_all(ris)

        # ── 5. BOISSONS ─────────────────────────────────────────────
        boissons_data = [
            Boisson(id=1,  nom='Béninoise 60',        prix_unitaire=600.0),
            Boisson(id=2,  nom='Béninoise 33',        prix_unitaire=350.0),
            Boisson(id=3,  nom='Aquabell',            prix_unitaire=600.0),
            Boisson(id=4,  nom='Awooyo',              prix_unitaire=1000.0),
            Boisson(id=5,  nom='BB lager 60',         prix_unitaire=800.0),
            Boisson(id=6,  nom='Beaufort 33',         prix_unitaire=500.0),
            Boisson(id=7,  nom='Beaufort 50',         prix_unitaire=600.0),
            Boisson(id=8,  nom='Buldozer',            prix_unitaire=800.0),
            Boisson(id=9,  nom='Castel 50',           prix_unitaire=600.0),
            Boisson(id=10, nom='Chill 33',            prix_unitaire=400.0),
            Boisson(id=11, nom='Chill 50',            prix_unitaire=600.0),
            Boisson(id=12, nom='Coca 60',             prix_unitaire=500.0),
            Boisson(id=13, nom='Comtesse eau',        prix_unitaire=600.0),
            Boisson(id=14, nom='Comtesse fruit',      prix_unitaire=600.0),
            Boisson(id=15, nom='Desperados bouteille',prix_unitaire=2000.0),
            Boisson(id=16, nom='Doppel Energy',       prix_unitaire=600.0),
        ]
        db.session.add_all(boissons_data)

        # ── 6. CAISSIER ─────────────────────────────────────────────
        caissier = Caissier(id=1, nom='Archange')
        db.session.add(caissier)
        db.session.commit()

        # ── 7. DONNÉES HISTORIQUES (Aug 2025 – Jan 2026) ────────────
        boissons_map = {b.id: b for b in Boisson.query.all()}
        compositions = defaultdict(list)
        for ri in RecetteIngredient.query.all():
            compositions[ri.recette_id].append(
                (ri.ingredient_id, ri.quantite, ri.ingredient.unite)
            )

        spagh  = Recette.query.filter(Recette.nom.ilike('%spaghetti%')).all()
        legumes= Recette.query.filter(Recette.nom.ilike('%légume%')).all()
        chaw   = Recette.query.filter(Recette.nom.ilike('%chawarma%')).first()

        bprops_raw = {
            1: 0.22, 2: 0.18, 5: 0.13, 9: 0.09, 6: 0.08, 7: 0.08,
            10: 0.07, 11: 0.05, 12: 0.04, 8: 0.03, 14: 0.02, 13: 0.01,
        }
        tot = sum(bprops_raw.values())
        bprops = {k: v/tot for k, v in bprops_raw.items()}

        def distribute(recette_list, total_qty):
            if not recette_list or total_qty <= 0:
                return []
            weights = [random.uniform(0.6, 1.4) for _ in recette_list]
            s = sum(weights)
            return [(r.id, max(0, round(total_qty * w / s)))
                    for r, w in zip(recette_list, weights) if round(total_qty * w / s) > 0]

        ventes_par_jour = defaultdict(list)
        start, end = date(2025, 8, 1), date(2026, 1, 31)
        current = start

        nb_v = nb_s = nb_t = nb_e = 0

        while current <= end:
            dow = current.weekday()
            if dow == 5:
                food_min, food_max = 130_000, 200_000
                bar_min,  bar_max  = 420_000, 700_000
                chaw_pct = 0.13
            elif dow == 4:
                food_min, food_max =  55_000, 100_000
                bar_min,  bar_max  = 180_000, 300_000
                chaw_pct = 0.09
            elif dow == 6:
                food_min, food_max =  70_000, 130_000
                bar_min,  bar_max  = 220_000, 380_000
                chaw_pct = 0.09
            else:
                food_min, food_max =  20_000,  40_000
                bar_min,  bar_max  =  60_000, 150_000
                chaw_pct = 0.04

            food_target = random.uniform(food_min, food_max)
            bar_target  = random.uniform(bar_min,  bar_max)
            if random.random() < 0.05:
                food_target *= random.uniform(0.3, 0.6)
                bar_target  *= random.uniform(0.3, 0.5)

            nb_dishes = max(1, int(food_target / 1450))
            spagh_qty  = round(nb_dishes * 0.36)
            legume_qty = round(nb_dishes * max(0.10, 1.0 - 0.36 - chaw_pct - 0.05))
            chaw_qty   = round(nb_dishes * chaw_pct)

            assignments = (distribute(spagh, spagh_qty)
                           + distribute(legumes, legume_qty)
                           + ([(chaw.id, chaw_qty)] if chaw and chaw_qty > 0 else []))

            day_ventes = []
            for rid, qty in assignments:
                if qty > 0:
                    dt = datetime(current.year, current.month, current.day,
                                  random.randint(11, 21), random.randint(0, 59))
                    v = Vente(recette_id=rid, quantite=qty, date=dt)
                    db.session.add(v)
                    day_ventes.append((rid, qty))
                    nb_v += 1
            ventes_par_jour[current] = day_ventes

            # Session caisse bar
            montant_reel = round(bar_target)
            sess = SessionCaisse(date=current, caissier_id=1,
                                  montant_reel=montant_reel,
                                  montant_attendu=0.0, ecart=0.0)
            db.session.add(sess)
            db.session.flush()

            montant_attendu = 0.0
            for bid, prop in bprops.items():
                b = boissons_map.get(bid)
                if not b or b.prix_unitaire <= 0:
                    continue
                qte = round(bar_target * prop / b.prix_unitaire)
                if qte <= 0:
                    continue
                db.session.add(SessionLigne(
                    session_id=sess.id, boisson_id=bid,
                    stock_initial=0.0, entrees=float(qte), stock_final=0.0,
                    prix_unitaire_snap=b.prix_unitaire
                ))
                montant_attendu += qte * b.prix_unitaire

            sess.montant_attendu = round(montant_attendu, 2)
            sess.ecart = round(montant_reel - montant_attendu, 2)
            nb_s += 1
            current += timedelta(days=1)

        db.session.commit()

        # ── Transferts magasin → cuisine ────────────────────────────
        for jour, day_v in sorted(ventes_par_jour.items()):
            besoins = defaultdict(float)
            ingr_unite = {}
            for rid, qte_vendue in day_v:
                for ingr_id, qty_pp, unite in compositions.get(rid, []):
                    besoins[ingr_id] += qte_vendue * qty_pp
                    ingr_unite[ingr_id] = unite
            for ingr_id, qty_total in besoins.items():
                qty = round(qty_total * random.uniform(1.05, 1.15), 2)
                dt = datetime(jour.year, jour.month, jour.day,
                              random.randint(6, 9), random.randint(0, 59))
                db.session.add(HistoriqueTransfert(
                    ingredient_id=ingr_id, quantite=qty,
                    unite=ingr_unite[ingr_id], date=dt,
                    sens='magasin_vers_cuisine'
                ))
                nb_t += 1

        db.session.commit()

        # ── Entrées boissons (livraisons bar) ───────────────────────
        conso = defaultdict(lambda: defaultdict(float))
        for sl in SessionLigne.query.all():
            sess = db.session.get(SessionCaisse, sl.session_id)
            if sess:
                conso[sess.date][sl.boisson_id] += sl.entrees

        par_semaine = defaultdict(lambda: defaultdict(float))
        for d, bids in conso.items():
            lundi = d - timedelta(days=d.weekday())
            for bid, qty in bids.items():
                par_semaine[lundi][bid] += qty

        for lundi in sorted(par_semaine):
            jeudi = lundi + timedelta(days=3)
            for bid, qty_sem in par_semaine[lundi].items():
                b = boissons_map.get(bid)
                if not b:
                    continue
                pct = random.uniform(0.60, 0.70)
                qty_lun = max(1, round(qty_sem * pct * random.uniform(1.05, 1.10)))
                db.session.add(EntreeBoisson(
                    boisson_id=bid, quantite=float(qty_lun), date=lundi,
                    note=f"Livraison sem. {lundi.strftime('%d/%m/%Y')}"
                ))
                nb_e += 1
                if random.random() < 0.85:
                    qty_jeu = max(1, round(qty_sem * (1 - pct) * random.uniform(1.05, 1.10)))
                    db.session.add(EntreeBoisson(
                        boisson_id=bid, quantite=float(qty_jeu), date=jeudi,
                        note=f"Réappro {jeudi.strftime('%d/%m/%Y')}"
                    ))
                    nb_e += 1

        db.session.commit()

        print(f"Initialisation terminée :")
        print(f"  Ventes cuisine   : {nb_v}")
        print(f"  Sessions bar     : {nb_s}")
        print(f"  Transferts       : {nb_t}")
        print(f"  Livraisons bar   : {nb_e}")


if __name__ == '__main__':
    seed()
