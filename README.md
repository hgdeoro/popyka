![popyka.png](docs%2Fpopyka.png)

* Main repository at **GitLab**: https://gitlab.com/hgdeoro/popyka
* Mirror at **GitHub**: https://github.com/hgdeoro/popyka

[![Hatch project](https://img.shields.io/badge/Packaging-Hatch-blue)](.)
[![Apache License](https://img.shields.io/badge/License-Apache-blue)](.)
[![Python](https://img.shields.io/badge/Python-3.10%2C%203.11%2C%203.12-blue)](.)
[![PostgreSql](https://img.shields.io/badge/PostgreSql-12%2C%2013%2C%2014%2C%2015%2C%2016-blue)](.)
[![pipeline status](https://gitlab.com/hgdeoro/popyka/badges/main/pipeline.svg)](https://gitlab.com/hgdeoro/popyka/-/commits/main)
[![Latest Release](https://gitlab.com/hgdeoro/popyka/-/badges/release.svg)](https://gitlab.com/hgdeoro/popyka/-/releases)

Tox results:

![py310-pg12](https://img.shields.io/badge/py3.10%2Bpg12-passed-green)
![py310-pg13](https://img.shields.io/badge/py3.10%2Bpg13-passed-green)
![py310-pg14](https://img.shields.io/badge/py3.10%2Bpg14-passed-green)
![py310-pg15](https://img.shields.io/badge/py3.10%2Bpg15-passed-green)
![py310-pg16](https://img.shields.io/badge/py3.10%2Bpg16-passed-green)
![py311-pg12](https://img.shields.io/badge/py3.11%2Bpg12-passed-green)
![py311-pg13](https://img.shields.io/badge/py3.11%2Bpg13-passed-green)
![py311-pg14](https://img.shields.io/badge/py3.11%2Bpg14-passed-green)
![py311-pg15](https://img.shields.io/badge/py3.11%2Bpg15-passed-green)
![py311-pg16](https://img.shields.io/badge/py3.11%2Bpg16-passed-green)
![py312-pg12](https://img.shields.io/badge/py3.12%2Bpg12-passed-green)
![py312-pg13](https://img.shields.io/badge/py3.12%2Bpg13-passed-green)
![py312-pg14](https://img.shields.io/badge/py3.12%2Bpg14-passed-green)
![py312-pg15](https://img.shields.io/badge/py3.12%2Bpg15-passed-green)
![py312-pg16](https://img.shields.io/badge/py3.12%2Bpg16-passed-green)

# MVP (v1.0)

* Supported versions of **Python**: ~~3.8~~, ~~3.9~~, `3.10`, `3.11`, `3.12`
* Supported versions of **PostgreSql**: `12`, `13`, `14`, `15`, `16`

### Status

The MVP is under development on the `main` branch.

TODO (the list is still changing):
1. create mechanism to allow inclusion of user's Python code (processors)
1. _dev experience_: generate documentation of public API
1. _ci/cd_: build image from release tag
1. _ci/cd_: publish docker image to public repository
1. _ci/cd_: add coverage & badge
1. ~~_ci/cd_: run unittests~~ **DONE**
1. ~~add mechanism to overwrite path to configuration file~~ **DONE**
1. ~~implement e2e test~~ **DONE**
1. ~~improve configuration mechanism to support real world scenarios~~ **DONE**
1. ~~_dev experience_: create sample projects using popyka~~ *DONE**
1. ~~fix issues on MacOS (for local development, it requires `--network=host`)~~ **DONE**
1. ~~improve automated testing~~ **DONE**
1. ~~define supported Python versions and run tests on all supported versions~~ **DONE**
1. ~~implement semantic versioning~~ **DONE**


# PoC (v0.1)

### Status

* The Proof of Concept is **finished** (`v0.1.0`)
* To clone it: `git clone git@gitlab.com:hgdeoro/popyka.git --branch v0.1.0`
* To now more about the process to go from zero to PoC you can read my blog post: [From Zero to CDC: A 3-days Agile Journey to the PoC](https://hdo.dev/posts/20240406-popyka/).

### Code

So far the code is small, everything fits in [__main__.py](../blob/v0.1.0/popyka/__main__.py?ref_type=tags).


```mermaid
sequenceDiagram
    Main->>Postgres: create_replication_slot()
    Main->>Postgres: start_replication()
    Postgres->>ReplicationConsumerToProcessorAdaptor: wal2json change
    ReplicationConsumerToProcessorAdaptor->>IgnoreTxFilter: ignore_change()
    ReplicationConsumerToProcessorAdaptor->>LogChangeProcessor: process_change()
    ReplicationConsumerToProcessorAdaptor->>ProduceToKafkaProcessor: process_change()
    ProduceToKafkaProcessor->>Kafka: publish()
    ReplicationConsumerToProcessorAdaptor->>Postgres: flush_lsn
```

### PoC: run locally

Clone the PoC:

    $ git clone git@gitlab.com:hgdeoro/popyka.git --branch v0.1.0

Launch PostgreSql and Kafka using docker compose:

    $ make docker-compose-up
    $ make docker-compose-wait  # wait util services are up

Simulate some DB activity (insert, update, delete):

    $ make docker-db-activity-simulator-run

Run PoPyKa to read the changes from PostgreSql and write JSONs to Kafka:

    $ make docker-popyka-run-gitlab

or building the image locally (if you want to try your changes):

    $ make docker-popyka-build
    $ make docker-popyka-run


You can see the contents of the Kafka topic using ~~Kowl~~ Redpanda Console at http://localhost:8080/topics/popyka

**List of captured changes streamed to Kafka**:

![kafka-topic.png](docs%2Fkafka-topic.png)

**Insert**:

![cdc-insert.png](docs%2Fcdc-insert.png)

**Update**:

![cdc-update.png](docs%2Fcdc-update.png)

**Delete**:

![cdc-delete.png](docs%2Fcdc-delete.png)
