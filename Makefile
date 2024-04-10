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

docker-compose-logs:
	docker compose logs -f

docker-compose-wait:
	while /bin/true ; do\
 		nc -z localhost 5434 || echo "Waiting for PostgreSql..." ; \
 		nc -z localhost 9094 || echo "Waiting for Kafka..." ; \
 		nc -z localhost 5434 && nc -z localhost 9094 && break ; \
 		sleep 1 ; \
	done

# ----------

tox-docker-compose-build-all:
	docker compose --project-name popyka-tox --file docker-compose-tox.yml \
		build \
			--build-arg HTTP_PROXY=$$http_proxy \
			--build-arg HTTPS_PROXY=$$https_proxy \
			pg12 pg13 pg14 pg15 pg16
	docker compose --project-name popyka-tox --file docker-compose-tox.yml \
		up -d pg12 pg13 pg14 pg15 pg16

# ----------

docker-popyka-run-gitlab:
	# docker container run using host network to keep it similar to running code locally
	docker run --rm -ti --network host \
		-e POPYKA_DB_DSN=$(TEST_POPYKA_DB_DSN_SAMPLE_1_DB) \
		-e POPYKA_KAFKA_CONF_DICT=$(TEST_POPYKA_KAFKA_CONF_DICT) \
			registry.gitlab.com/hgdeoro/popyka/test

# ----------

TEST_POPYKA_DB_DSN_POSTGRES_DB = "postgresql://postgres:pass@localhost:5434/postgres"
TEST_POPYKA_DB_DSN_SAMPLE_1_DB = "postgresql://postgres:pass@localhost:5434/sample_1"
TEST_POPYKA_KAFKA_CONF_DICT = '{"bootstrap.servers": "localhost:9094","client.id": "popyka-client"}'

docker-popyka-build:
	docker build --build-arg HTTP_PROXY=$$http_proxy --build-arg HTTPS_PROXY=$$https_proxy -t local-popyka .

docker-popyka-run:
	# docker container run using host network to keep it similar to running code locally
	docker run --rm -ti --network host \
		-e POPYKA_DB_DSN=$(TEST_POPYKA_DB_DSN_SAMPLE_1_DB) \
		-e POPYKA_KAFKA_CONF_DICT=$(TEST_POPYKA_KAFKA_CONF_DICT) \
			local-popyka

docker-db-activity-simulator-run:
	# docker container run using host network to keep it similar to running code locally
	docker build -t db-activity-simulator ./tests/docker/db-activity-simulator
	docker run --network host --rm -ti \
		-e DSN_CHECK_DB=$(TEST_POPYKA_DB_DSN_POSTGRES_DB) \
		-e DSN_ACTIVITY_SIMULATOR=$(TEST_POPYKA_DB_DSN_SAMPLE_1_DB) \
			db-activity-simulator

local-run:
	env \
		POPYKA_DB_DSN=$(POPYKA_DB_DSN_POSTGRES_DB) \
		POPYKA_KAFKA_CONF_DICT=$(POPYKA_KAFKA_CONF_DICT) \
			./venv/bin/python3 -m popyka

test:
	$(VENVDIR)/bin/pytest -v

test-all:
	env EXPLORATION_TEST=1 $(VENVDIR)/bin/pytest -v


# ----------

release:
	$(VENVDIR)/bin/hatch version $$($(VENVDIR)/bin/hatch version | cut -d. -f1,2,3)
	git commit popyka/__version__.py -m "Bump version"
	git tag -a v$$($(VENVDIR)/bin/hatch version) -m "New version: $$($(VENVDIR)/bin/hatch version)"
	$(VENVDIR)/bin/hatch version dev
	git commit popyka/__version__.py -m "Bump version"
