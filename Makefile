# This Makefile is intended to be used by development
# 'local' means running the code locally (using PostgreSql & Kafka from docker compose)
# 'docker' means running the code in the docker image (also using PostgreSql & Kafka from docker compose)

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
	$(VENVDIR)/bin/pip-compile -o reqs/requirements-prod.txt reqs/requirements-prod.in
	$(VENVDIR)/bin/pip-compile -o reqs/requirements-dev.txt  reqs/requirements-dev.in

pip-compile-upgrade: ## Compiles dependencies (pip-tools) into requirements-*.txt checking for new versions
	$(VENVDIR)/bin/pip-compile --upgrade -o reqs/requirements-prod.txt reqs/requirements-prod.in
	$(VENVDIR)/bin/pip-compile --upgrade -o reqs/requirements-dev.txt  reqs/requirements-dev.in

pip-sync: ## Run pip-sync (pip-tools)
	$(VENVDIR)/bin/pip-sync reqs/requirements-prod.txt reqs/requirements-dev.txt

docker-compose-up: ## Brings up required service for local development
	docker compose up -d

docker-compose-logs: ## Shows logs of docker compose services
	docker compose logs -f

docker-compose-wait: ## Busy-waits until the services are up
	while : ; do\
 		nc -z localhost 5434 || echo "Waiting for PostgreSql..." ; \
 		nc -z localhost 9094 || echo "Waiting for Kafka..." ; \
 		nc -z localhost 5434 && nc -z localhost 9094 && break ; \
 		sleep 1 ; \
	done

# ----------

tox-docker-compose-build-all: ## [tox] Build and start containers required for running Tox
	docker compose --project-name popyka-tox --file docker-compose-tox.yml \
		build \
			--build-arg HTTP_PROXY=$$http_proxy \
			--build-arg HTTPS_PROXY=$$https_proxy \
			pg12 pg13 pg14 pg15 pg16
	docker compose --project-name popyka-tox --file docker-compose-tox.yml \
		up -d pg12 pg13 pg14 pg15 pg16

tox-docker-compose-wait: ## [tox] Busy-waits until the services required for running Tox are up
	while /bin/true ; do \
 		nc -z localhost 54012 && \
 			nc -zv localhost 54013 && \
 			nc -zv localhost 54014 && \
 			nc -zv localhost 54015 && \
 			nc -zv localhost 54016 && \
 			break ; \
 		sleep 0.5 ;\
	done

tox: tox-docker-compose-build-all ## [tox] Run tox (run pytest on all supported combinations)
	tox --result-json tox-result.json

tox-quick: tox-docker-compose-build-all ## [tox] Run tox on oldest and newest Python/PostgreSql
	tox -e py310-pg12,py312-pg16

# ----------

docker-popyka-run-gitlab:
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

release-patch:
	$(VENVDIR)/bin/hatch version $$($(VENVDIR)/bin/hatch version | cut -d. -f1,2,3)
	git commit popyka/__version__.py -m "Bump version"
	git tag -a v$$($(VENVDIR)/bin/hatch version) -m "New version: $$($(VENVDIR)/bin/hatch version)"
	$(VENVDIR)/bin/hatch version dev
	git commit popyka/__version__.py -m "Bump version"

release-minor:
	$(VENVDIR)/bin/hatch version $$($(VENVDIR)/bin/hatch version | cut -d. -f1,2,3)
	$(VENVDIR)/bin/hatch version minor
	git commit popyka/__version__.py -m "Bump version"
	git tag -a v$$($(VENVDIR)/bin/hatch version) -m "New version: $$($(VENVDIR)/bin/hatch version)"
	$(VENVDIR)/bin/hatch version dev
	git commit popyka/__version__.py -m "Bump version"
