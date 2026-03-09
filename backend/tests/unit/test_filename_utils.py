from app.utils.filename import build_voucher_filename, sanitize_filename_component


def test_sanitize_filename_component_removes_illegal_chars() -> None:
    raw = "  海南/百迈:科*?  "
    cleaned = sanitize_filename_component(raw, fallback="fallback")
    assert "/" not in cleaned
    assert ":" not in cleaned
    assert "*" not in cleaned
    assert "?" not in cleaned


def test_build_voucher_filename_uses_fallbacks() -> None:
    filename = build_voucher_filename(subject=None, month=None, voucher_no=None)
    assert filename == "unknown-subject-unknown-month-unknown-no.pdf"


def test_build_voucher_filename_nominal() -> None:
    filename = build_voucher_filename("测试公司", "2024-01", "记12")
    assert filename == "测试公司-2024-01-记12.pdf"
