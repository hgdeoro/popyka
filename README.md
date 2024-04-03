Run tests:

    /tmp$ git clone git@gitlab.com:hgdeoro/popyka.git
    /tmp$ cd popyka/
    /tmp/popyka (main)$ python3 -m venv venv
    /tmp/popyka (main)$ source venv/bin/activate
    (venv) /tmp/popyka (main)$ pip install -r requirements.txt
    (venv) /tmp/popyka (main)$ docker compose up -d
    (venv) /tmp/popyka (main)$ pytest tests/test_plugin.py::test_test_decoding_plugin
    (venv) /tmp/popyka (main)$ pytest tests/test_plugin.py::test_pgoutput_plugin
