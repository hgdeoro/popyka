from popyka.config import FilterConfig
from popyka.core import Filter
from tests.conftest_all_scenarios import AllScenarios

DEFAULT_DICT_CONFIG_IGNORE_TX_FILTER = {
    "class": "popyka.builtin.filters.IgnoreTxFilter",
    "config": {},
}


def test_instantiate_builtin_ignore_tx_filter_works():
    filter_config = FilterConfig.from_dict(DEFAULT_DICT_CONFIG_IGNORE_TX_FILTER)
    instance = filter_config.instantiate()
    assert str(instance.__class__) == "<class 'popyka.builtin.filters.IgnoreTxFilter'>"


class TestIgnoreTxFilterAllScenarios:
    def test_filter_doesnt_fails(self, all_scenarios: AllScenarios):
        filter_config = FilterConfig.from_dict(DEFAULT_DICT_CONFIG_IGNORE_TX_FILTER)
        filter_instance: Filter = filter_config.instantiate()
        for change in all_scenarios.expected:
            filter_instance.ignore_change(change)

    def test_tx_are_filtered_out(self, all_scenarios: AllScenarios):
        filter_config = FilterConfig.from_dict(DEFAULT_DICT_CONFIG_IGNORE_TX_FILTER)
        flt: Filter = filter_config.instantiate()
        actions_before_filter = {_["action"] for _ in all_scenarios.expected}
        assert actions_before_filter == {"B", "C", "I", "U", "D", "T", "M"}

        actions_after_filter = {_["action"] for _ in all_scenarios.expected if not flt.ignore_change(_)}

        assert actions_after_filter == {"I", "U", "D", "T", "M"}
