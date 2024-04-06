SHELL := /bin/bash

PYTHON ?= python3.11
VENVDIR ?= $(abspath ./venv)

export PATH := $(VENVDIR)/bin:$(PATH)

LOCAL_DSN = "host=localhost port=5434 dbname=postgres user=postgres"
KAFKA_CONF_DICT = '{"bootstrap.servers": "localhost:9094","client.id": "popyka-client"}'

venv:
	$(PYTHON) -m venv venv
	$(VENVDIR)/bin/pip install pip-tools

pip-compile:
	$(VENVDIR)/bin/pip-compile -o reqs/requirements-prod.txt reqs/requirements-prod.in
	$(VENVDIR)/bin/pip-compile -o reqs/requirements-dev.txt  reqs/requirements-dev.in

pip-compile-upgrade:
	$(VENVDIR)/bin/pip-compile --upgrade -o reqs/requirements-prod.txt reqs/requirements-prod.in
	$(VENVDIR)/bin/pip-compile --upgrade -o reqs/requirements-dev.txt  reqs/requirements-dev.in

pip-sync:
	$(VENVDIR)/bin/pip-sync reqs/requirements-prod.txt reqs/requirements-dev.txt


pip-compile-sync: pip-compile pip-sync


local-run:
	env \
		DSN=$(LOCAL_DSN) \
		KAFKA_CONF_DICT=$(KAFKA_CONF_DICT) \
		./venv/bin/python3 -m popyka
