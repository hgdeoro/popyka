.PHONY: help

SHELL := /bin/bash

PYTHON ?= python3.11
VENVDIR ?= $(abspath ./venv)

export PATH := $(VENVDIR)/bin:$(PATH)

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

venv: ## Creates the Python virtualenv for local development
	$(PYTHON) -m venv venv
	$(VENVDIR)/bin/pip install pip-tools

pip-compile: ## Compiles dependencies (pip-tools) into requirements-*.txt
	$(VENVDIR)/bin/pip-compile -o requirements.txt requirements.in

pip-compile-upgrade: ## Compiles dependencies (pip-tools) into requirements-*.txt checking for new versions
	$(VENVDIR)/bin/pip-compile --upgrade -o requirements.txt requirements.in

pip-sync: ## Run pip-sync (pip-tools)
	$(VENVDIR)/bin/pip-sync requirements.txt

docker-compose-rm:
	docker compose rm --force --stop --volumes
