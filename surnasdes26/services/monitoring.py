def monitoring_target_progress(completed, raw_target):
    """Return optional target/progress without failing on an unset target."""
    if raw_target is None or raw_target == "":
        return None, None
    try:
        target = int(raw_target)
    except (TypeError, ValueError):
        return None, None
    if target <= 0:
        return None, None
    return target, round((completed / target) * 100, 1)
