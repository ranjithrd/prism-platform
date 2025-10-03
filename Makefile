# Installs dependencies from poetry.lock
install: 
	poetry install

# Runs the app in development mode with auto-reload
dev: 
	poetry run uvicorn src.main:app --reload

# Runs the app in a production-ready way using Gunicorn
run:
	poetry run gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.main:app

.PHONY: install dev run