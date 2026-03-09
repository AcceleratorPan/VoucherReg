from __future__ import annotations


class MockOCRService:
    def __init__(self, mock_text: str | None = None) -> None:
        self.mock_text = mock_text or (
            "核算单位: 海南百迈科医疗科技股份有限公司\n"
            "业务日期: 2022年7月31日\n"
            "凭证字号: 记-470\n"
        )

    async def recognize(self, image_bytes: bytes, image_url: str | None = None) -> str:  # noqa: ARG002
        return self.mock_text
