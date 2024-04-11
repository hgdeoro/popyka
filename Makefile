# This Makefile is intended to be used by development
# 'local' means running the code locally (using PostgreSql & Kafka from docker compose)
# 'docker' means running the code in the docker image (also using PostgreSql & Kafka from docker compose)

.PHONY: help

SHELL := /bin/bash

PYTHON ?= python3.11
VENVDIR ?= $(abspath ./venv)
DOCKER_COMPOSE_LOCAL_DEVELOPMENT_SERVICES ?= pg16 kafka kowl
DOCKER_COMPOSE_TOX_SERVICES ?= pg12 pg13 pg14 pg15 pg16

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
	docker compose up --remove-orphans -d $(DOCKER_COMPOSE_LOCAL_DEVELOPMENT_SERVICES)

docker-compose-logs: ## Shows logs of docker compose services used for local development
	docker compose logs -f $(DOCKER_COMPOSE_LOCAL_DEVELOPMENT_SERVICES)

docker-compose-wait: ## Busy-waits until the services are up
	while /bin/true ; do \
		nc -zv localhost 9094 && \
			nc -zv localhost 54016 && \
			nc -zv localhost 8080 && \
			break ; \
 		sleep 0.5 ;\
	done

# ----------

tox-docker-compose-build: ## [tox] Build containers required for running Tox
	docker compose build \
			--build-arg HTTP_PROXY=$$http_proxy \
			--build-arg HTTPS_PROXY=$$https_proxy \
			$(DOCKER_COMPOSE_TOX_SERVICES)

tox-docker-compose-start: ## [tox] Start containers required for running Tox
	docker compose up -d $(DOCKER_COMPOSE_TOX_SERVICES)

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

tox: tox-docker-compose-start ## [tox] Run tox (run pytest on all supported combinations)
	tox --result-json tox-result.json

tox-quick: tox-docker-compose-start ## [tox] Run tox on oldest and newest Python/PostgreSql
	tox -e py310-pg12,py312-pg16

# ----------

docker-popyka-run-gitlab:
	docker run --rm -ti --network host \
		-e POPYKA_DB_DSN=$(DOCKER_COMPOSE_POPYKA_DB_DSN_SAMPLE_1) \
		-e POPYKA_KAFKA_CONF_DICT=$(DOCKER_COMPOSE_POPYKA_KAFKA_CONF_DICT) \
			registry.gitlab.com/hgdeoro/popyka/test

# ----------

DOCKER_COMPOSE_POPYKA_DB_DSN_POSTGRES = "postgresql://postgres:pass@pg16:5432/postgres"
DOCKER_COMPOSE_POPYKA_DB_DSN_SAMPLE_1 = "postgresql://postgres:pass@pg16:5432/sample_1"
DOCKER_COMPOSE_POPYKA_KAFKA_CONF_DICT = '{"bootstrap.servers": "kafka:9092","client.id": "popyka-client"}'

LOCAL_POPYKA_DB_DSN_POSTGRES = "postgresql://postgres:pass@localhost:54016/postgres"
LOCAL_POPYKA_DB_DSN_SAMPLE_1 = "postgresql://postgres:pass@localhost:54016/sample_1"
LOCAL_POPYKA_KAFKA_CONF_DICT = '{"bootstrap.servers": "localhost:9094","client.id": "popyka-client"}'

docker-compose-db-activity-simulator:
	docker compose up db-activity-simulator

docker-compose-popyka-run:
	docker compose up popyka

#docker-popyka-run:
#	# docker container run using host network to keep it similar to running code locally
#	docker run --rm -ti --network host \
#		-e POPYKA_DB_DSN=$(DOCKER_COMPOSE_POPYKA_DB_DSN_SAMPLE_1) \
#		-e POPYKA_KAFKA_CONF_DICT=$(DOCKER_COMPOSE_POPYKA_KAFKA_CONF_DICT) \
#			local-popyka

local-run:
	env \
		POPYKA_DB_DSN=$(LOCAL_POPYKA_DB_DSN_SAMPLE_1) \
		POPYKA_KAFKA_CONF_DICT=$(LOCAL_POPYKA_KAFKA_CONF_DICT) \
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
