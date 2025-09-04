# ==== Makefile pour l'application Streamlit Financier ====

# Variables
PYTHON = python3
PIP = pip
APP = app.py

# Installation des dépendances principales (production)
install:
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

# Installation des dépendances de développement
install-dev: install
	$(PIP) install -r requirements-dev.txt

# Lancer l'application Streamlit
run:
	streamlit run $(APP)

# Lancer les tests
test:
	pytest -v

# Lancer mkdocs en local pour la documentation
docs-serve:
	mkdocs serve

# Construire la documentation statique
docs-build:
	mkdocs build

# Nettoyage des fichiers temporaires
clean:
	rm -rf __pycache__ .pytest_cache .streamlit/cache .mypy_cache
	rm -rf site

# Mise à jour des dépendances (freeze)
freeze:
	$(PIP) freeze > requirements-freeze.txt
