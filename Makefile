# Makefile for AODA Compliance Checker

.PHONY: help install setup test run-web run-cli clean lint format

help:
	@echo "AODA Compliance Checker - Available commands:"
	@echo ""
	@echo "  make install    - Install dependencies"
	@echo "  make setup      - Full setup (create venv, install deps, install playwright)"
	@echo "  make test       - Run tests"
	@echo "  make run-web    - Start web interface"
	@echo "  make run-cli    - Run CLI scan (requires URL env var)"
	@echo "  make clean      - Clean generated files"
	@echo "  make lint       - Run linters"
	@echo "  make format     - Format code with black"
	@echo ""

install:
	pip install -r requirements.txt
	playwright install chromium

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt
	. .venv/bin/activate && playwright install chromium
	mkdir -p reports static
	@echo "✅ Setup complete! Activate venv with: source .venv/bin/activate"

test:
	pytest tests/ -v

run-web:
	python main.py web

run-cli:
	@if [ -z "$(URL)" ]; then \
		echo "Error: URL variable not set. Usage: make run-cli URL=https://example.com"; \
		exit 1; \
	fi
	python main.py scan --url $(URL)

clean:
	rm -rf reports/*.pdf
	rm -rf __pycache__
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete

lint:
	flake8 src/ tests/ main.py --max-line-length=100 --ignore=E501,W503

format:
	black src/ tests/ main.py --line-length=100

dev-install:
	pip install black flake8 pytest pytest-asyncio

.DEFAULT_GOAL := help

