import pytz
from sqlalchemy import DateTime, TypeDecorator


class AwareDateTime(TypeDecorator):
    """Results returned as aware datetime, not naive ones."""

    impl = DateTime(timezone=True)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        tz = pytz.timezone("Europe/Warsaw")
        aware_datetime = value.replace(tzinfo=pytz.utc).astimezone(tz)
        return aware_datetime
