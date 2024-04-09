FROM postgres:15

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y postgresql-15-wal2json && rm -rf /var/lib/apt/lists/*
