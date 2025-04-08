from datetime import datetime, timedelta, timezone


def ensure_date_type(
    value: str | int | float | datetime, tz_offset_hours: int = 8
) -> str:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, int | float):
        dt = datetime.fromtimestamp(value / 1000 if value > 1e12 else value)
    elif isinstance(value, str):
        try:
            ts = float(value)
            dt = datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts)
        except ValueError as error:
            raise ValueError(f'無法解析時間字串：{value}') from error
    else:
        raise TypeError(f'不支援的時間格式：{type(value)}')

    tz = timezone(timedelta(hours=tz_offset_hours))
    dt = dt.astimezone(tz)

    return dt.strftime('%Y-%m-%d')
