# Installs dependencies from poetry.lock
install: 
	poetry install

# Runs the app in development mode with auto-reload
dev: 
	poetry run uvicorn src.main:app --reload

# Runs the app in a production-ready way using Gunicorn
run:
	poetry run gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.main:app

PORT ?=8030

run-worker:
	poetry run gunicorn -w 1 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$(PORT) src.worker:app 

dev-worker:
	poetry run uvicorn src.worker:app --reload --port $(PORT)

install-frontend:
	cd frontend && npm install && cd ..

build-frontend:
	cd frontend && npm run build && cd ..

serve-frontend:
	cd frontend && npm run serve && cd ..

.PHONY: install dev run