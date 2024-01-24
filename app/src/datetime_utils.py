from datetime import datetime

import pytz


def aware_datetime_field(init_dt: datetime) -> datetime:
    aware_datetime = init_dt.replace(tzinfo=pytz.utc)

    return aware_datetime
