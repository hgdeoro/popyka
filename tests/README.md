# Type of tests

The tests are not 100% precisely defined, but as a general rule we follow the idea of the **test pyramid**:

* `system_tests`: test the whole system.
* `functional_tests`: test a component, but accessing other components or systems.
* `unit_tests`: test a single component, in isolation, preferably without access to DB or Kafka.

We have also:

* `contract_tests`: test the contract with external services.
  * `test_wal2json_scenarios.py` is the most important: here we test how wal2json behaves,
    in different Python/PostgreSql combinations.
* `exploration_tests`: tests used for learning purposes.
