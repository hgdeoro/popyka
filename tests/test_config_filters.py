from popyka.config import FilterConfig


def test_instantiate_builtin_ignore_tx_filter_works():
    filter_config = FilterConfig.from_yaml(
        {
            "class": "popyka.builtin.filters.IgnoreTxFilter",
            "config": {},
        }
    )
    instance = filter_config.instantiate()
    assert str(instance.__class__) == "<class 'popyka.builtin.filters.IgnoreTxFilter'>"
