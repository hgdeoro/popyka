FROM postgres:14

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y postgresql-14-wal2json && rm -rf /var/lib/apt/lists/*
