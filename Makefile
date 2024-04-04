LOCAL_DSN = "host=localhost port=5434 dbname=postgres user=postgres"
KAFKA_CONF_DICT = '{"bootstrap.servers": "localhost:9094","client.id": "popyka-client"}'

local-run:
	env \
		DSN=$(LOCAL_DSN) \
		KAFKA_CONF_DICT=$(KAFKA_CONF_DICT) \
		./venv/bin/python3 -m popyka
