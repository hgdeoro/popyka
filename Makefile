# This Makefile is intended to be used by development
# 'local' means running the code locally (using PostgreSql & Kafka from docker compose)
# 'docker' means running the code in the docker image (also using PostgreSql & Kafka from docker compose)

.PHONY: help

SHELL := /bin/bash

DOCKER_IMAGE_TAG_RELEASE := registry.gitlab.com/hgdeoro/popyka:v0.2.3

PYTHON310 ?= python3.10
PYTHON311 ?= python3.11
PYTHON312 ?= python3.12

PYTHON := $(PYTHON312)

VENVDIR_310 ?= $(abspath ./venv-3.10)
VENVDIR_311 ?= $(abspath ./venv-3.11)
VENVDIR_312 ?= $(abspath ./venv-3.12)

VENVDIR := $(VENVDIR_312)

DOCKER_COMPOSE_LOCAL_DEVELOPMENT_SERVICES ?= pg16 kafka kowl
DOCKER_COMPOSE_TOX_SERVICES ?= pg12 pg13 pg14 pg15 pg16

export PATH := $(VENVDIR)/bin:$(PATH)
export DOCKER_IMAGE_TAG_RELEASE := $(DOCKER_IMAGE_TAG_RELEASE)

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

venv: ## Creates the Python virtualenv for local development
	$(PYTHON310) -m venv $(VENVDIR_310)
	$(VENVDIR_310)/bin/pip install pip-tools

	$(PYTHON311) -m venv $(VENVDIR_311)
	$(VENVDIR_311)/bin/pip install pip-tools

	$(PYTHON312) -m venv $(VENVDIR_312)
	$(VENVDIR_312)/bin/pip install pip-tools

pip-compile: ## Compiles dependencies (pip-tools) into requirements-*.txt
	$(VENVDIR_310)/bin/pip-compile -o reqs/requirements-prod-3.10.txt                                    reqs/requirements-prod.in
	$(VENVDIR_310)/bin/pip-compile -o reqs/requirements-dev-3.10.txt  -c reqs/requirements-prod-3.10.txt reqs/requirements-dev.in

	$(VENVDIR_311)/bin/pip-compile -o reqs/requirements-prod-3.11.txt                                    reqs/requirements-prod.in
	$(VENVDIR_311)/bin/pip-compile -o reqs/requirements-dev-3.11.txt  -c reqs/requirements-prod-3.11.txt reqs/requirements-dev.in

	$(VENVDIR_312)/bin/pip-compile -o reqs/requirements-prod-3.12.txt                                    reqs/requirements-prod.in
	$(VENVDIR_312)/bin/pip-compile -o reqs/requirements-dev-3.12.txt  -c reqs/requirements-prod-3.12.txt reqs/requirements-dev.in

pip-compile-upgrade: ## Compiles dependencies (pip-tools) into requirements-*.txt checking for new versions
	$(VENVDIR_310)/bin/pip-compile --upgrade -o reqs/requirements-prod-3.10.txt                                    reqs/requirements-prod.in
	$(VENVDIR_310)/bin/pip-compile --upgrade -o reqs/requirements-dev-3.10.txt  -c reqs/requirements-prod-3.10.txt reqs/requirements-dev.in

	$(VENVDIR_311)/bin/pip-compile --upgrade -o reqs/requirements-prod-3.11.txt                                    reqs/requirements-prod.in
	$(VENVDIR_311)/bin/pip-compile --upgrade -o reqs/requirements-dev-3.11.txt  -c reqs/requirements-prod-3.11.txt reqs/requirements-dev.in

	$(VENVDIR_312)/bin/pip-compile --upgrade -o reqs/requirements-prod-3.12.txt                                    reqs/requirements-prod.in
	$(VENVDIR_312)/bin/pip-compile --upgrade -o reqs/requirements-dev-3.12.txt  -c reqs/requirements-prod-3.12.txt reqs/requirements-dev.in

pip-sync: ## Run pip-sync (pip-tools)
	$(VENVDIR_310)/bin/pip-sync reqs/requirements-prod-3.10.txt reqs/requirements-dev-3.10.txt
	$(VENVDIR_311)/bin/pip-sync reqs/requirements-prod-3.11.txt reqs/requirements-dev-3.11.txt
	$(VENVDIR_312)/bin/pip-sync reqs/requirements-prod-3.12.txt reqs/requirements-dev-3.12.txt

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

tox-docker-compose-up: ## [tox] Start containers required for running Tox
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

# Do nothing when target doesn't matches. Needed to make `$(filter-out $@,$(MAKECMDGOALS))` work
# https://stackoverflow.com/questions/6273608/how-to-pass-argument-to-makefile-from-command-line
%:
    @:

tox: tox-docker-compose-up tox-docker-compose-wait ## [tox] Run tox (run pytest on all supported combinations)
	tox --result-json tox-result.json -- $(filter-out $@,$(MAKECMDGOALS))

tox-quick: tox-docker-compose-up tox-docker-compose-wait ## [tox] Run tox on oldest and newest Python/PostgreSql
	tox -e py310-pg12,py312-pg16 -- $(filter-out $@,$(MAKECMDGOALS))

# ----------

DOCKER_COMPOSE_POPYKA_DB_DSN_SAMPLE_1 = "postgresql://postgres:pass@pg16:5432/popyka_test"

LOCAL_POPYKA_DB_DSN_SAMPLE_1 = "postgresql://postgres:pass@localhost:54016/popyka_test"

# ----------

docker-popyka-run-gitlab: docker-compose-up  # Launch latest released version of Popyka.
	docker compose pull popyka-release
	docker compose up --build popyka-release db-activity-simulator

# ----------

docker-compose-db-activity-simulator:
	docker compose up db-activity-simulator

docker-compose-popyka-run:
	docker compose up popyka

local-run:
	env \
		POPYKA_DB_DSN=$(LOCAL_POPYKA_DB_DSN_SAMPLE_1) \
			./venv/bin/python3 -m popyka

test:  ## Run most important and fast tests
	$(VENVDIR)/bin/pytest -v

test-all:  ## Run all tests (except for system-tests)
	env EXPLORATION_TEST=1 SLOW_TEST=1 CONTRACT_TEST=1 SYSTEM_TEST_FAST=1 $(VENVDIR)/bin/pytest -v

coverage-unittest:
	pytest \
		--cov=popyka/ \
		--cov-report term \
		--cov-report html \
		--cov-report xml:coverage.xml \
		--cov-branch \
		tests/unit_tests/

coverage:
	pytest \
		--cov=popyka/ \
		--cov-report term \
		--cov-report html \
		--cov-report xml:coverage.xml \
		--cov-branch

# ----------

psql: ## connect to default test database
	psql $(LOCAL_POPYKA_DB_DSN_SAMPLE_1)

# ----------

test-system:
	env SYSTEM_TEST=1 SYSTEM_TEST_FAST=1 $(VENVDIR)/bin/pytest -vvs tests/system_tests/

test-system-sample-django-admin:
	docker compose --file samples/django-admin/docker-compose.yml build --quiet
	env SYSTEM_TEST=1 $(VENVDIR)/bin/pytest -vvs tests/system_tests/test_sample_django_admin.py

test-system-sample-django-admin-debug:
	docker compose --file samples/django-admin/docker-compose.yml build --quiet
	env SYSTEM_TEST=1 $(VENVDIR)/bin/pytest -vvs tests/system_tests/test_sample_django_admin.py --log-cli-level=DEBUG

# ----------

clean-docker:
	docker compose kill
	docker container prune -f
	docker volume prune -af

version-incr-dev:  ## Increment `.dev` version
	$(VENVDIR)/bin/hatch version | egrep '\.dev[[:digit:]]+$$'  # assert that we're in `.dev` version
	$(VENVDIR)/bin/hatch version dev                            # increment `.dev`

	git commit popyka/__version__.py -m "Bump version to $$($(VENVDIR)/bin/hatch version)"
	git tag v$$($(VENVDIR)/bin/hatch version) -m "New version: $$($(VENVDIR)/bin/hatch version)"

release-patch:  ## Release new version (using same PATCH) based on current .dev* version
	$(VENVDIR)/bin/hatch version | egrep '\.dev[[:digit:]]+$$' # assert that we're in `.dev` version
	$(VENVDIR)/bin/hatch version release                       # release: remove `.dev`
	sed -i "s#DOCKER_IMAGE_TAG_RELEASE := registry.gitlab.com/hgdeoro/popyka:v0.2.3

	git commit Makefile popyka/__version__.py -m "Bump version to $$($(VENVDIR)/bin/hatch version)"
	git tag v$$($(VENVDIR)/bin/hatch version) -m "New version: $$($(VENVDIR)/bin/hatch version)"

	$(VENVDIR)/bin/hatch version patch,dev
	git commit popyka/__version__.py -m "Bump version to $$($(VENVDIR)/bin/hatch version)"

release-minor:  ## Release new version (incrementing MINOR) based on current .dev* version
	$(VENVDIR)/bin/hatch version | egrep '\.dev[[:digit:]]+$$' # assert that we're in `.dev` version
	$(VENVDIR)/bin/hatch version release,minor                 # release: remove `.dev`, incr `minor`
	sed -i "s#DOCKER_IMAGE_TAG_RELEASE := registry.gitlab.com/hgdeoro/popyka:v0.2.3

	git commit Makefile popyka/__version__.py -m "Bump version to $$($(VENVDIR)/bin/hatch version)"
	git tag v$$($(VENVDIR)/bin/hatch version) -m "New version: $$($(VENVDIR)/bin/hatch version)"

	$(VENVDIR)/bin/hatch version patch,dev
	git commit popyka/__version__.py -m "Bump version to $$($(VENVDIR)/bin/hatch version)"
