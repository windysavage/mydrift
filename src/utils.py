import hashlib
import re
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


def decode_content(content_str: str) -> str:
    try:
        content_str.encode('utf-8')
        return content_str
    except UnicodeEncodeError:
        try:
            return content_str.encode('latin1').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            return content_str


def mask_urls(text: str) -> str:
    return re.sub(r'https?://\S+', '[LINK]', text)


def generate_message_chunk_id(start_ts: int, end_ts: int, senders: list[str]) -> str:
    base = f'{start_ts}-{end_ts}-{"-".join(sorted(senders))}'
    return hashlib.md5(base.encode()).hexdigest()


def generate_gmail_chunk_id(on_date: str, message_id: str) -> str:
    base = f'{on_date}-{message_id}'
    return hashlib.md5(base.encode()).hexdigest()
