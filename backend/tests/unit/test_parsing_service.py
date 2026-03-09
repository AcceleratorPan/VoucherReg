from app.services.parsing.parser import ParsingService


def test_normalize_text_compacts_whitespace() -> None:
    service = ParsingService()
    result = service.normalize_text("核算单位：A公司\r\n\r\n凭证号：记-001")
    assert "\r" not in result
    assert "核算单位" in result


def test_extract_subject_month_voucher_no() -> None:
    service = ParsingService()
    text = "核算单位: 海南百迈科医疗科技股份有限公司\n业务日期: 2022年7月31日\n凭证字号: 记—470"

    assert service.extract_subject(text) == "海南百迈科医疗科技股份有限公司"
    assert service.extract_month(text) == "2022-07"
    assert service.extract_voucher_no(text) == "记470"


def test_parse_returns_preview_and_confidence() -> None:
    service = ParsingService()
    text = "单位名称: 测试公司\n日期: 2024-03-15\n凭证号: 记-88"

    parsed = service.parse(text)

    assert parsed.subject == "测试公司"
    assert parsed.month == "2024-03"
    assert parsed.voucher_no == "记88"
    assert parsed.file_name_preview.endswith(".pdf")
    assert parsed.confidence > 0.0
