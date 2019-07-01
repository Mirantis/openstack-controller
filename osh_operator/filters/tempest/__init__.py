from osh_operator.filters.tempest.conf import SECTIONS


def generate_tempest_config(spec, helmbundle_spec):
    config = {}

    for ts in SECTIONS:
        ts_inst = ts(spec, helmbundle_spec)
        config[ts_inst.name] = {}
        opts = {}
        for opt in ts_inst.options:
            val = getattr(ts_inst, opt)
            if val is not None:
                opts[opt] = val

        config[ts_inst.name] = opts

    return config
