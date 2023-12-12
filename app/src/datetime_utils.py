from datetime import datetime

import pytz


def aware_datetime_field(init_dt: datetime) -> datetime:
    tz = pytz.timezone("Europe/Warsaw")
    aware_datetime = init_dt.replace(tzinfo=pytz.utc).astimezone(tz)

    return aware_datetime
