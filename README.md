# Lotus Garden — Stock Restaurant

Application Flask de gestion des stocks (cuisine & bar) pour Lotus Garden :

- **Cuisine**
  - Ingrédients (stock magasin/cuisine)
  - Recettes et ventes (décrémentation automatique du stock)
  - Transferts (magasin ↔ cuisine)
  - Tableau de bord : **Top plats** sur période, **export CSV**, **PDF période**

- **Bar / Caisse**
  - Boissons (prix unitaire)
  - Sessions de caisse (par période de service)
  - Pointage par boisson : `SI + Entrées − SF`
  - Tableau de bord : **Top boissons** sur période, **export CSV**

## 🚀 Installation

### Prérequis
- Python 3.10+
- pip

### 1) Créer un virtualenv & installer
```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
