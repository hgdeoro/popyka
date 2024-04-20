FROM postgres:12

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y postgresql-12-wal2json && rm -rf /var/lib/apt/lists/*

COPY ../postgresql-init.sh /docker-entrypoint-initdb.d/postgresql-init.sh
