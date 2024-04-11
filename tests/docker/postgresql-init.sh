#!/bin/bash

set -eux

cat <<EOF

                                    888
                                    888
                                    888
88888b.   .d88b.  88888b.  888  888 888  888  8888b.
888 "88b d88""88b 888 "88b 888  888 888 .88P     "88b
888  888 888  888 888  888 888  888 888888K  .d888888
888 d88P Y88..88P 888 d88P Y88b 888 888 "88b 888  888
88888P"   "Y88P"  88888P"   "Y88888 888  888 "Y888888
888               888           888
888               888      Y8b d88P
888               888       "Y88P"


EOF

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
	CREATE USER popyka_test WITH PASSWORD 'popyka_test';
	CREATE USER popyka_tox WITH PASSWORD 'popyka_tox';
	CREATE DATABASE popyka_test;
	CREATE DATABASE popyka_tox;
	GRANT ALL PRIVILEGES ON DATABASE popyka_test TO popyka_test;
	GRANT ALL PRIVILEGES ON DATABASE popyka_tox TO popyka_tox;
EOSQL
