* Main repository at **GitLab**: https://gitlab.com/hgdeoro/popyka
* Mirror at **GitHub**: https://github.com/hgdeoro/popyka

[![Hatch project](https://img.shields.io/badge/Packaging-Hatch-blue)](.)
[![Apache License](https://img.shields.io/badge/License-Apache-blue)](.)
[![Latest Release](https://gitlab.com/hgdeoro/popyka/-/badges/release.svg)](https://gitlab.com/hgdeoro/popyka/-/releases)
[![pipeline status](https://gitlab.com/hgdeoro/popyka/badges/main/pipeline.svg)](https://gitlab.com/hgdeoro/popyka/-/commits/main)

Supported versions of **Python**:

![Python](https://img.shields.io/badge/Python-3.10-blue)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Python](https://img.shields.io/badge/Python-3.12-blue)

Supported versions of **PostgreSql**:

![PostgreSql](https://img.shields.io/badge/PostgreSql-12-blue)
![PostgreSql](https://img.shields.io/badge/PostgreSql-13-blue)
![PostgreSql](https://img.shields.io/badge/PostgreSql-14-blue)
![PostgreSql](https://img.shields.io/badge/PostgreSql-15-blue)
![PostgreSql](https://img.shields.io/badge/PostgreSql-16-blue)

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




# Popyka

Effortless and extendable data change capture (CDC) with Python.

![popyka.png](docs%2Fpopyka.png)

Change data capture (CDC) refers to the process of capturing changes made to the data
in a database and then delivering those changes in real-time to a downstream system.

### In case you missed it

* PoC: [README-PoC.md](README-PoC.md) & [From Zero to CDC: A 3-days Agile Journey to the PoC](https://hdo.dev/posts/20240406-popyka/).
* [Implementing a system test for Popyka](https://hdo.dev/posts/20240417-system-testing-and-python/).

## Why a new CDC system?

Existing CDC options can be overly complex and resource-intensive, hindering adoption by smaller systems.

> Popyka is a simpler CDC solution that gets you started in minutes.

* Built for agility and ease of use.
* Simplifies CDC operations.
* Works with PostgreSql (12, 13, 14, 15, 16) and `wal2json`.
* Works with Python 3.10, 3.11, 3.12.
* Built in `Filters` and `Processor`
* Tailor it to your needs: easily extensible through custom `Filters` and `Processors`,
    letting you adapt it to your specific workflows.

[//]: # (Implementing custom `Filters` and `Processors` is easy, and allows you to)
[//]: # (write to **Kafka** the messages in a way that can be easily consumed downstream.)
[//]: # (This will usually contain business logic, This can be implemented using any)
[//]: # (fo the supported Python versions.)

> Streamline Data Delivery with Custom Filters and Processors

Popyka empowers you to write custom filters and processors in Python to tailor
data messages for downstream **Kafka** consumers. This functionality seamlessly
integrates your own business logic, giving you complete control over the data transformation process.

[//]: # (The system is not limited to **Kafka**: you can implement your own `Processor`)
[//]: # (to write the data wherever you need &#40;**Redis**, **S3**, **Snowflake**, **Cassandra**, other databases, etc.&#41;.)

> Unleash Data Delivery Flexibility

Popyka's custom **processors** empower you to write data to various destinations,
including **Redis**, **S3**, **Snowflake**, **Cassandra**, and more. Go beyond **Kafka** and tailor
your data pipeline to your specific needs.




## Stages

![stages.png](docs%2Fstages.png)

[//]: # (Popyka receives the changes from PostgreSql using the logical replication protocol,)
[//]: # (for each `BEGIN`, `COMMIT`, `INSERT`, `UPDATE`, `DELETE` and `TRUNCATE` operation.)
[//]: # ()
[//]: # (In the **first stage** we filter the messages: we decide which messages need to be processed,)
[//]: # (and which need to be ignored.)
[//]: # ()
[//]: # (In the **second stage** we process those messages that were not filtered out. Each message)
[//]: # (is passed to all processor instances, one by one.)

Popyka leverages PostgreSQL's logical replication protocol to capture all data changes
(`BEGIN`, `COMMIT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`) efficiently.

**Filters** allows you to focus on specific messages based on your requirements.

**Processors** are the workhorses of Popyka. They take the captured data,
transform it as needed (think of it as data wrangling), and then send it
to other systems to keep everyone in sync.

[//]: # (The default configuration uses:)
[//]: # ()
[//]: # (* `IgnoreTxFilter` to ignore those changes associated to `BEGIN` and `COMMIT`.)
[//]: # (* `LogChangeProcessor`: to log the received messages.)
[//]: # (* `ProduceToKafkaProcessor`: to publish a message to Kafka.)




## Filters

[//]: # (Popyka ensures you only process the data you care about. It achieves this by letting you configure)
[//]: # (filters that act like checkpoints, allowing only relevant changes to proceed)

Popyka ensures you only process the data you care about. It achieves this by letting you configure
filters that act like smart sieves, allowing only relevant changes to proceed.

[//]: # (Only the relevant changes are processed by Popyka. It does this by first passing)
[//]: # (each change through filters you configure. These filters are like smart sieves,)
[//]: # (letting through only the data you need.)

![filter-result.png](docs%2Ffilter-result.png)

Popyka filters offer three actions:

* `IGNORE` discards the change (any remaining filter is ignored),
* `PROCESS` accepts it (any remaining filter is ignored),
* `CONTINUE` sends it to subsequent filters for evaluation.

Popyka provides [built filters](popyka%2Fbuiltin%2Ffilters.py): `IgnoreTxFilter` and `TableNameIgnoreFilter`.

**Extending Popyka**

Extend Popyka's filtering capabilities by inheriting from the `Filter` class
and implementing the `filter()` method. This method should return a value from the Result enum,
indicating whether to `IGNORE`, `PROCESS`, or `CONTINUE` filtering the data change.

```python
class MyCustomFilter(Filter):
    def filter(self, change) -> Result:
        ...
```

The base `Filter` class is defined in [api.py](popyka%2Fapi.py).




## Processors

[//]: # (After filtering, Popyka sends the data changes through its processors one by one,)
[//]: # (following the order you configured them in. Each processor can perform its specific task on the data.)

[//]: # (Filtered changes are delivered to all configured processors in the order they are defined.)
[//]: # (Each processor has the opportunity to manipulate the data as needed and export it to other systems.)

Processors take the filtered changes and manipulate them according to your needs (think of it as data transformation).
Processors then export the transformed data to external systems.

Popyka simplifies sending data changes to **Kafka**. It includes a [built-in processor](popyka%2Fbuiltin%2Fprocessors.py) `ProduceToKafkaProcessor`
that lets you easily export the database changes to your **Kafka** cluster, keeping your other systems in sync.

**Extending Popyka**

You can extend Popyka's processing capabilities by inheriting from the `Processor` class and implementing the `process_change()` method.

```python
class MyCustomProcessor(Processor):
    def process_change(self, change):
        ...
```

The base `Processor` class is defined in [api.py](popyka%2Fapi.py).




## Configuration

The basic configuration is done using environment variables:

* `POPYKA_CONFIG`: Path to configuration file. If unset, uses default configuration: [popyka-default.yaml](popyka/popyka-default.yaml).
  * Example: `/etc/popyka/config.yaml`
* `POPYKA_PYTHONPATH`: Directories to add to the python path.
* `POPYKA_COMPACT_DUMP`.

#### Default configuration file

The default configuration file is [popyka-default.yaml](popyka/popyka-default.yaml).
It uses bash-style environment variables interpolation, and requires to set:

* `POPYKA_DB_DSN`: libpq-compatible connection URI.
  * Example: `postgresql://hostname:5432/database-name`
  * See: [Connection URIs](https://www.postgresql.org/docs/16/libpq-connect.html#LIBPQ-CONNSTRING-URIS)
* `POPYKA_KAFKA_BOOTSTRAP_SERVERS`: Kafka bootstrap servers, comma separated.
  * Example: `bootstrap-server-1:9092,bootstrap-server-2:9092,bootstrap-server-3:9092`
  * See: [Apache Kafka Python Client](https://docs.confluent.io/kafka-clients/python/current/overview.html)

Other environment variables that you can use with the **default** configuration file:

* `POPYKA_DB_SLOT_NAME`: A unique, cluster-wide identifier for the PostgreSql logical replication slot.
* `POPYKA_KAFKA_TOPIC`: Kafka topic name where the changes should be published to.

### Reference & sample projects

#### Django Admin

To launch the **Django Admin** demo:

```shell
$ cd samples/django-admin  # cd into sample project

$ docker compose up -d  # bring all the services up: PostgreSql, Kafka, popyka.
                        # You might need to repeat this command.

$ docker compose logs -f demo-popyka  # to see the CDC working
```

* Navigate to [django admin](http://localhost:8081/admin/) and login using `admin`:`admin`.
* You can see **Kafka** contents using [RedPanda console](http://localhost:8082/).

You might find this files of interest:

* Code & README: [samples/django-admin](./samples/django-admin/)
* [docker-compose.yml](./samples/django-admin/docker-compose.yml)
* Default config: [popyka-default.yaml](./popyka/popyka-default.yaml)
* Alternative config: [popyka-config-ignore-tables.yaml](./samples/django-admin/popyka-config/popyka-config-ignore-tables.yaml)




# Under development

The v1 is under development on the `main` branch.

1. create mechanism to allow inclusion of user's Python code (docker)
1. _dev experience_: generate documentation of public API
1. ~~create mechanism to allow inclusion of user's Python code (docker compose)~~ **DONE**
1. ~~document usage~~ **DONE**
1. ~~_ci/cd_: run system tests~~ **DONE**
1. ~~_ci/cd_: publish docker image to public repository~~ **DONE**
1. ~~_ci/cd_: add coverage &~~ badge
1. ~~_ci/cd_: build image from release tag~~ **DONE**
1. ~~_ci/cd_: run unittests~~ **DONE**
1. ~~add mechanism to overwrite path to configuration file~~ **DONE**
1. ~~implement e2e test~~ **DONE**
1. ~~improve configuration mechanism to support real world scenarios~~ **DONE**
1. ~~_dev experience_: create sample projects using popyka~~ *DONE**
1. ~~fix issues on MacOS (for local development, it requires `--network=host`)~~ **DONE**
1. ~~improve automated testing~~ **DONE**
1. ~~define supported Python versions and run tests on all supported versions~~ **DONE**
1. ~~implement semantic versioning~~ **DONE**
