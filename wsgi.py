"""
wsgi.py — Point d'entrée gunicorn.
Initialise la DB (tables + données demo) avant de servir l'app.
"""
try:
    from demo_init import seed
    seed()
except Exception as exc:
    print(f"[wsgi] Avertissement : seed() a échoué ({exc}), démarrage sans données demo.")

from app import app  # noqa: E402
