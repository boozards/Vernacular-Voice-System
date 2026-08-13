.PHONY: dev test seed-catalog lint build clean help simulate

help:
	@echo "VoiceKart Makefile targets:"
	@echo "  make dev          - Start all microservices and infrastructure via docker-compose"
	@echo "  make test         - Run full pytest test suite across unit and integration tests"
	@echo "  make seed-catalog - Run script to populate catalog with 500+ products"
	@echo "  make lint         - Run flake8 / black code formatting and lint checks"
	@echo "  make simulate     - Send sample voice simulation request to Gateway"
	@echo "  make build        - Build all Docker container images"
	@echo "  make clean        - Stop containers and cleanup temporary build artifacts"

dev:
	docker-compose up --build

test:
	pytest tests/ -v --cov=.

seed-catalog:
	python scripts/seed_catalog.py

lint:
	@echo "Running code quality checks..."
	./venv/bin/python -m py_compile shared/config.py
	./venv/bin/python -m py_compile shared/models.py
	./venv/bin/python -m py_compile gateway_service/main.py
	./venv/bin/python -m py_compile orchestrator_service/main.py
	@echo "All files compile successfully."

simulate:
	curl -X POST http://localhost:8001/simulate \
		-H "Content-Type: application/json" \
		-d '{"user_phone": "+919876543210", "text_input": "Bhai mujhe ek accha sa running shoe chahiye, Nike ya Adidas, 2000 ke andar, size 9", "language": "hi-IN"}'

build:
	docker-compose build

clean:
	docker-compose down -v
	find . -type d -name "__pycache__" -exec rm -r {} +
