# Installs dependencies from poetry.lock
install: 
	poetry install --with gui

install-server:
	poetry install

# Runs the app in development mode with auto-reload
dev: 
	poetry run uvicorn src.main:app --reload

dev-frontend:
	cd frontend && npm run dev

PORT ?=8000

# Runs the app in a production-ready way using Gunicorn
run:
	PORT=$(PORT) poetry run gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.main:app

run-worker:
	poetry run python run_gui.py

build-worker:
	poetry run pyinstaller PRISM_Platform.spec --noconfirm

install-frontend:
	cd frontend && npm install && cd ..

build-frontend:
	cd frontend && npm run build && cd ..

serve-frontend:
	cd frontend && npm run serve && cd ..

.PHONY: install dev run