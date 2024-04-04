LOCAL_DSN = "host=localhost port=5434 dbname=postgres user=postgres"

local-run:
	env DSN=$(LOCAL_DSN) \
		./venv/bin/python3 -m popyka
