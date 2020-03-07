from constants import game_states


operators = {
    "equal": lambda x, y: x == y,
    "less_or_equal": lambda x, y: x <= y,
    "greater_or_equal": lambda x, y: x >= y,
    "not_equal": lambda x, y: x != y,
}


def eval_obj_state(obj, state_name=None):
    """
    Evaluates whether given object meets provided state's definition
    - state_name defaults to none to allow for indiscriminate use
    """
    if not state_name:
        return True

    state_def = game_states[state_name]
    state_attr = getattr(obj, state_def["stat"])
    state_qual = state_def["value"]
    if isinstance(state_attr, list):
        state_attr = len(state_attr)

    return operators[state_def["operator"]](state_attr, state_qual)


def search_by_obj(objs, obj_name, obj_state=None):
    return list(
        filter(
            lambda x: x.name == obj_name and eval_obj_state(x, obj_state), objs
        )
    )


def search_by_tag(objs, obj_tag, obj_state=None):
    return list(
        filter(
            lambda x: obj_tag in x.tags and eval_obj_state(x, obj_state), objs
        )
    )
