# This Makefile is intended to be used by development
# 'local' means running the code locally (using PostgreSql & Kafka from docker compose)
# 'docker' means running the code in the docker image (also using PostgreSql & Kafka from docker compose)

SHELL := /bin/bash

PYTHON ?= python3.11
VENVDIR ?= $(abspath ./venv)

export PATH := $(VENVDIR)/bin:$(PATH)

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

docker-compose-up:
	docker compose up -d

# ----------

TEST_DSN_POSTGRES = "postgresql://postgres:pass@localhost:5434/postgres"
TEST_DSN_SAMPLE_1 = "postgresql://postgres:pass@localhost:5434/sample_1"
TEST_KAFKA_CONF_DICT = '{"bootstrap.servers": "localhost:9094","client.id": "popyka-client"}'

docker-popyka-build:
	docker build --build-arg HTTP_PROXY=$$http_proxy --build-arg HTTPS_PROXY=$$https_proxy -t local-popyka .

docker-popyka-run:
	# docker container run using host network to keep it similar to running code locally
	env \
		DSN=$(TEST_DSN_SAMPLE_1) \
		KAFKA_CONF_DICT=$(TEST_KAFKA_CONF_DICT) \
			docker run --rm -ti --network host -e DSN -e KAFKA_CONF_DICT \
				local-popyka python3 -m popyka

docker-db-activity-simulator-run:
	# docker container run using host network to keep it similar to running code locally
	docker build -t db-activity-simulator ./tests/docker/db-activity-simulator
	docker run --network host --rm -ti \
		-e DSN=$(TEST_DSN_SAMPLE_1) \
		-e DSN_CREATE_DB=$(TEST_DSN_POSTGRES) \
			db-activity-simulator

local-run:
	env \
		DSN=$(TEST_DSN_POSTGRES) \
		KAFKA_CONF_DICT=$(TEST_KAFKA_CONF_DICT) \
		./venv/bin/python3 -m popyka
