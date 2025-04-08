import hashlib
import re


def decode_content(content_str: str) -> str:
    return content_str.encode('latin1').decode('utf-8')


def mask_urls(text: str) -> str:
    return re.sub(r'https?://\S+', '[LINK]', text)


def generate_message_chunk_id(start_ts: int, end_ts: int, senders: list[str]) -> str:
    base = f'{start_ts}-{end_ts}-{"-".join(sorted(senders))}'
    return hashlib.md5(base.encode()).hexdigest()


def generate_gmail_chunk_id(on_date: str, message_id: str) -> str:
    base = f'{on_date}-{message_id}'
    return hashlib.md5(base.encode()).hexdigest()
