SHELL := /bin/bash

PYTHON ?= python3.11
VENVDIR ?= $(abspath ./venv)

export PATH := $(VENVDIR)/bin:$(PATH)

LOCAL_DSN = "postgresql://postgres:pass@localhost:5434/postgres"
LOCAL_DSN_SAMPLE_1 = "postgresql://postgres:pass@localhost:5434/sample_1"
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

docker-build-popyka:
	docker build --build-arg HTTP_PROXY=$$http_proxy --build-arg HTTPS_PROXY=$$https_proxy -t local-popyka .

docker-run-popyka:
	env \
		DSN=$(LOCAL_DSN_SAMPLE_1) \
		KAFKA_CONF_DICT=$(KAFKA_CONF_DICT) \
			docker run --rm -ti --network host -e DSN -e KAFKA_CONF_DICT \
				local-popyka python3 -m popyka

docker-run-db-activity-simulator:
	docker build -t db-activity-simulator ./tests/docker/db-activity-simulator
	docker run --network host --rm -ti -e DSN=$(LOCAL_DSN_SAMPLE_1) db-activity-simulator

local-run:
	env \
		DSN=$(LOCAL_DSN) \
		KAFKA_CONF_DICT=$(KAFKA_CONF_DICT) \
		./venv/bin/python3 -m popyka
