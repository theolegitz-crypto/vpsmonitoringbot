import re
from datetime import timedelta


DURATION_PATTERN = re.compile(r"^(?P<value>\d+)(?P<unit>[mhdw])$")


def parse_duration(value: str) -> timedelta:
    match = DURATION_PATTERN.match(value.strip().lower())
    if not match:
        raise ValueError("Duration must look like 30m, 2h, 1d or 1w")

    amount = int(match.group("value"))
    unit = match.group("unit")

    if unit == "m":
        return timedelta(minutes=amount)
    if unit == "h":
        return timedelta(hours=amount)
    if unit == "d":
        return timedelta(days=amount)
    return timedelta(weeks=amount)

