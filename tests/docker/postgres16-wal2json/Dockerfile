FROM docker.io/library/postgres:16

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y postgresql-16-wal2json && rm -rf /var/lib/apt/lists/*

COPY ../postgresql-init.sh /docker-entrypoint-initdb.d/postgresql-init.sh
