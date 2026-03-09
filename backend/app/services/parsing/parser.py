from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.utils.filename import build_voucher_filename, sanitize_filename_component

_SUBJECT_PATTERNS = [
    re.compile(r"(?:核算单位|单位名称|公司名称)\s*[:：]?\s*([^\n]{2,120})"),
]

_MONTH_PATTERNS = [
    re.compile(r"(20\d{2})\s*[年/\-.]\s*(\d{1,2})\s*(?:[月/\-.]\s*\d{1,2}\s*日?)?"),
]

_VOUCHER_NO_PATTERNS = [
    re.compile(r"(?:凭证(?:号|编号|字号)?\s*[:：]?\s*)?([记收付转])\s*[\-—–]?\s*(\d{1,8})"),
]


@dataclass
class ParsedVoucherResult:
    subject: str | None
    month: str | None
    voucher_no: str | None
    confidence: float
    needs_user_review: bool
    file_name_preview: str


class ParsingService:
    def normalize_text(self, raw_text: str) -> str:
        normalized = unicodedata.normalize("NFKC", raw_text or "")
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"[ \t]+", " ", normalized)
        return normalized.strip()

    def extract_subject(self, text: str) -> str | None:
        for pattern in _SUBJECT_PATTERNS:
            match = pattern.search(text)
            if match:
                return sanitize_filename_component(match.group(1).strip(), fallback="", max_len=120) or None
        return None

    def extract_month(self, text: str) -> str | None:
        for pattern in _MONTH_PATTERNS:
            match = pattern.search(text)
            if not match:
                continue
            year = int(match.group(1))
            month = int(match.group(2))
            if 1 <= month <= 12:
                return f"{year:04d}-{month:02d}"
        return None

    def extract_voucher_no(self, text: str) -> str | None:
        for pattern in _VOUCHER_NO_PATTERNS:
            match = pattern.search(text)
            if match:
                prefix = match.group(1)
                no = match.group(2).lstrip("0") or "0"
                return f"{prefix}{no}"
        return None

    def estimate_confidence(self, subject: str | None, month: str | None, voucher_no: str | None) -> float:
        score = 0.0
        score += 0.4 if subject else 0.0
        score += 0.3 if month else 0.0
        score += 0.3 if voucher_no else 0.0
        return round(score, 2)

    def parse(self, raw_ocr_text: str) -> ParsedVoucherResult:
        normalized = self.normalize_text(raw_ocr_text)
        subject = self.extract_subject(normalized)
        month = self.extract_month(normalized)
        voucher_no = self.extract_voucher_no(normalized)
        confidence = self.estimate_confidence(subject, month, voucher_no)
        needs_user_review = confidence < 0.95

        return ParsedVoucherResult(
            subject=subject,
            month=month,
            voucher_no=voucher_no,
            confidence=confidence,
            needs_user_review=needs_user_review,
            file_name_preview=build_voucher_filename(subject, month, voucher_no),
        )
