.PHONY: install run dev worker beat build up
install:
	pip install -r requirements.txt

run:
	uvicorn main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn main:app --reload

worker:
	celery -A worker.celery_app worker --loglevel=info

beat:
	celery -A worker.celery_app beat --loglevel=info

build:
	docker build -t hrx-chat .

up:
	docker-compose up --build
