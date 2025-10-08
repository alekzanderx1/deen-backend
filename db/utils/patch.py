def apply_updates(instance, data: dict):
    for k, v in data.items():
        if v is not None:
            setattr(instance, k, v)
    return instance
