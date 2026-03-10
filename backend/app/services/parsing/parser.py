from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.utils.filename import build_voucher_filename, sanitize_filename_component

_SUBJECT_LABELS = ("核算单位", "校算单位", "单位名称", "公司名称")
_DATE_LABELS = ("业务日期", "日期")
_VOUCHER_LABELS = ("凭证编号", "凭证字号", "凭证号", "编号")


def _build_spaced_label_pattern(label: str) -> str:
    return r"\s*".join(re.escape(char) for char in label if not char.isspace())


def _build_label_group_pattern(labels: tuple[str, ...]) -> str:
    ordered_labels = sorted(labels, key=len, reverse=True)
    return "|".join(_build_spaced_label_pattern(label) for label in ordered_labels)


_ALL_FIELD_LABEL_PATTERN = _build_label_group_pattern(_SUBJECT_LABELS + _DATE_LABELS + _VOUCHER_LABELS)


def _compile_labeled_value_pattern(labels: tuple[str, ...], max_chars: int) -> re.Pattern[str]:
    label_pattern = _build_label_group_pattern(labels)
    return re.compile(
        rf"(?:{label_pattern})\s*[:：]?(?:[ \t]*\n)?[ \t]*(?P<value>(?!(?:{_ALL_FIELD_LABEL_PATTERN})\s*[:：]?)[\s\S]{{1,{max_chars}}}?)(?=\s*(?:\n|$|(?:{_ALL_FIELD_LABEL_PATTERN})\s*[:：]?))"
    )


_SUBJECT_PATTERN = _compile_labeled_value_pattern(_SUBJECT_LABELS, max_chars=120)
_DATE_PATTERN = _compile_labeled_value_pattern(_DATE_LABELS, max_chars=40)
_VOUCHER_PATTERN = _compile_labeled_value_pattern(_VOUCHER_LABELS, max_chars=40)
_DATE_VALUE_PATTERN = re.compile(r"(20\d{2})\s*[年/\-.]\s*(\d{1,2})\s*(?:[月/\-.]\s*\d{1,2}\s*日?)?")
_VOUCHER_VALUE_PATTERN = re.compile(r"([记收付转])\s*[\-—–]?\s*(\d{1,8})")
_SUBJECT_TEXT_PATTERN = re.compile(r"[A-Za-z\u4e00-\u9fff]")
_SUBJECT_DATE_LIKE_PATTERN = re.compile(r"\d{1,4}[年/\-.]\d{1,2}(?:[月/\-.]\d{1,2}日?)?")
_SUBJECT_ORG_HINT_PATTERN = re.compile(
    r"(公司|集团|银行|医院|学校|大学|学院|中心|分公司|分行|支行|营业部|办事处|事务所|研究院|研究所|实验室|工会|"
    r"合作社|委员会|项目部|项目组|事业部|总部|分部|基地|门店|分店|厂|矿|店|站|局|院|所|社|部|处|室|队|行|司)$"
)
_SUBJECT_SUMMARY_WORD_PATTERN = re.compile(
    r"(安装|测试|维修|采购|销售|收款|付款|转账|报销|工资|社保|公积金|借款|还款|材料|货款|运费|租金|"
    r"水电|办公|差旅|运输|劳务|服务|样品|生产|加工|调拨)+"
)
_HEADER_STOP_PATTERN = re.compile(r"(摘要|借方|贷方|总账科目|明细科目|会计科目|科目编码|科目名称|数量|单价|金额|合计)")
_OCR_TEXT_NORMALIZATION_RULES = (
    (re.compile(r"[核校]\s*算\s*单\s*[位仪]"), "核算单位"),
)


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
        normalized = "\n".join(line.strip() for line in normalized.split("\n"))
        for pattern, replacement in _OCR_TEXT_NORMALIZATION_RULES:
            normalized = pattern.sub(replacement, normalized)
        return normalized.strip()

    def extract_subject(self, text: str) -> str | None:
        search_texts = [self._extract_header_text(text)]
        if text not in search_texts:
            search_texts.append(text)

        for search_text in search_texts:
            for value in self._extract_labeled_values(search_text, _SUBJECT_PATTERN):
                if not self._is_valid_subject_candidate(value):
                    continue
                sanitized = sanitize_filename_component(value, fallback="", max_len=120)
                if sanitized:
                    return sanitized
        return None

    def extract_month(self, text: str) -> str | None:
        labeled_value = self._extract_labeled_value(text, _DATE_PATTERN)
        if labeled_value:
            labeled_month = self._parse_month_value(labeled_value)
            if labeled_month:
                return labeled_month
        return self._parse_month_value(text)

    def extract_voucher_no(self, text: str) -> str | None:
        labeled_value = self._extract_labeled_value(text, _VOUCHER_PATTERN)
        if labeled_value:
            labeled_voucher_no = self._parse_voucher_value(labeled_value)
            if labeled_voucher_no:
                return labeled_voucher_no
        return self._parse_voucher_value(text)

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

    @staticmethod
    def _extract_labeled_value(text: str, pattern: re.Pattern[str]) -> str | None:
        match = pattern.search(text)
        if not match:
            return None
        value = match.group("value").strip().strip(":：")
        return value or None

    @staticmethod
    def _extract_labeled_values(text: str, pattern: re.Pattern[str]) -> list[str]:
        values: list[str] = []
        for match in pattern.finditer(text):
            value = match.group("value").strip().strip(":：")
            if value:
                values.append(value)
        return values

    @staticmethod
    def _parse_month_value(text: str) -> str | None:
        match = _DATE_VALUE_PATTERN.search(text)
        if not match:
            return None
        year = int(match.group(1))
        month = int(match.group(2))
        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}"
        return None

    @staticmethod
    def _parse_voucher_value(text: str) -> str | None:
        match = _VOUCHER_VALUE_PATTERN.search(text)
        if not match:
            return None
        prefix = match.group(1)
        no = match.group(2).lstrip("0") or "0"
        return f"{prefix}{no}"

    @staticmethod
    def _is_valid_subject_candidate(value: str) -> bool:
        compact = re.sub(r"\s+", "", value)
        if not compact:
            return False
        if not _SUBJECT_TEXT_PATTERN.search(compact):
            return False
        if _SUBJECT_DATE_LIKE_PATTERN.fullmatch(compact):
            return False
        if _VOUCHER_VALUE_PATTERN.fullmatch(compact):
            return False
        if _SUBJECT_SUMMARY_WORD_PATTERN.fullmatch(compact):
            return False
        if len(compact) < 6 and not _SUBJECT_ORG_HINT_PATTERN.search(compact):
            return False
        return True

    @staticmethod
    def _extract_header_text(text: str, max_lines: int = 10, max_chars: int = 400) -> str:
        if not text:
            return ""

        header_lines: list[str] = []
        total_chars = 0

        for raw_line in text.split("\n"):
            line = raw_line.strip()
            if not line:
                continue

            stop_match = _HEADER_STOP_PATTERN.search(line)
            if stop_match:
                prefix = line[: stop_match.start()].strip()
                if prefix:
                    header_lines.append(prefix)
                break

            header_lines.append(line)
            total_chars += len(line)
            if len(header_lines) >= max_lines or total_chars >= max_chars:
                break

        return "\n".join(header_lines).strip()
