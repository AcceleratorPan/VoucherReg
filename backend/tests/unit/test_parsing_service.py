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


def test_extract_fields_with_ocr_spacing_noise() -> None:
    service = ParsingService()
    text = "核 算 单 位 : 测试公司\n日 期 ：2024/03/15\n编 号 ：记 - 00088"

    parsed = service.parse(text)

    assert parsed.subject == "测试公司"
    assert parsed.month == "2024-03"
    assert parsed.voucher_no == "记88"


def test_extract_labeled_values_from_single_line_text() -> None:
    service = ParsingService()
    text = "扫描时间: 2026-03-10 核算单位：测试公司 日期：2024年3月15日 编号：记-470（记 - 470）"

    parsed = service.parse(text)

    assert parsed.subject == "测试公司"
    assert parsed.month == "2024-03"
    assert parsed.voucher_no == "记470"


def test_date_prefers_labeled_field_over_unrelated_date() -> None:
    service = ParsingService()
    text = "生成时间: 2026-03-10\n日期: 2024-03-15\n编号: 记-12"

    assert service.extract_month(service.normalize_text(text)) == "2024-03"


def test_empty_labeled_subject_does_not_capture_next_field() -> None:
    service = ParsingService()
    text = "核算单位:\n日期: 2024-03-15\n编号: 记-12"

    assert service.extract_subject(service.normalize_text(text)) is None


def test_subject_rejects_date_fragment() -> None:
    service = ParsingService()
    text = "核算单位: 5-01-13\n日期: 2025-01-13\n编号: 记-12"

    parsed = service.parse(text)

    assert parsed.subject is None
    assert parsed.month == "2025-01"
    assert parsed.voucher_no == "记12"


def test_subject_falls_back_to_full_ocr_text_after_table_headers() -> None:
    service = ParsingService()
    text = (
        "记账凭证\n"
        "日期：2025-11-29\n"
        "编号：记－1098\n"
        "页号；第1/2页\n"
        "会计科目\n"
        "借方\n"
        "贷方\n"
        "校算单位：海南建邦制药科技有限公司\n"
        "摘要\n"
        "安装调试\n"
    )

    parsed = service.parse(text)

    assert parsed.subject == "海南建邦制药科技有限公司"
    assert parsed.month == "2025-11"
    assert parsed.voucher_no == "记1098"


def test_subject_extracts_from_ocr_variant_xiaosuan_danyi() -> None:
    service = ParsingService()
    text = (
        "记账凭证\n"
        "日期：2025-11-29\n"
        "编号：记－1098\n"
        "页号：第2/2页\n"
        "1106\n"
        "发出商品\n"
        "校算单仪：海南建邦制药科技有限公司\n"
        "摘要\n"
        "安装调试\n"
    )

    parsed = service.parse(text)

    assert parsed.subject == "海南建邦制药科技有限公司"
    assert parsed.month == "2025-11"
    assert parsed.voucher_no == "记1098"


def test_subject_ignores_body_fake_label_after_table_header() -> None:
    service = ParsingService()
    text = (
        "记账凭证\n"
        "日期: 2025-01-13\n"
        "编号: 记-12\n"
        "摘要\n"
        "安装测试\n"
        "核算单位: 安装测试\n"
        "借方: 100.00"
    )

    parsed = service.parse(text)

    assert parsed.subject is None
    assert parsed.month == "2025-01"
    assert parsed.voucher_no == "记12"
