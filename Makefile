SHELL := /bin/bash

.PHONY: install-dev format lint typecheck test check env-verify

install-dev:
	python -m pip install -e '.[dev]'

format:
	ruff format .
	ruff check --fix .

lint:
	ruff format --check .
	ruff check .

typecheck:
	mypy src

test:
	pytest

check: lint typecheck test

env-verify:
	bash scripts/verify-env.sh
