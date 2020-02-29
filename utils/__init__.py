from constants import game_states


def eval_obj_state(obj, state_name=None):
    """
    Evaluates whether given object meets provided state's definition
    - state_name defaults to none to allow for indiscriminate use
    """
    if not state_name:
        return True

    state_def = game_states[state_name]
    state_attr = getattr(obj, state_def["stat"])
    print(f"Evaluating {obj.name}'s {state_name} state: {state_attr}")
    state_qual = state_def["value"]
    if isinstance(state_attr, list) and len(state_attr) == state_qual:
        return True
    elif state_attr == state_qual:
        return True

    return False


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
