from __future__ import annotations

import re

_ILLEGAL_FILENAME_CHARS = re.compile(r"[\\/:*?\"<>|]")
_WHITESPACE_RE = re.compile(r"\s+")


def sanitize_filename_component(value: str | None, fallback: str, max_len: int = 80) -> str:
    if not value:
        return fallback

    cleaned = _ILLEGAL_FILENAME_CHARS.sub("", value)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip().strip(".")

    if not cleaned:
        cleaned = fallback

    return cleaned[:max_len]


def build_voucher_filename(subject: str | None, month: str | None, voucher_no: str | None) -> str:
    safe_subject = sanitize_filename_component(subject, fallback="unknown-subject")
    safe_month = sanitize_filename_component(month, fallback="unknown-month", max_len=20)
    safe_voucher_no = sanitize_filename_component(voucher_no, fallback="unknown-no", max_len=30)
    return f"{safe_subject}-{safe_month}-{safe_voucher_no}.pdf"
