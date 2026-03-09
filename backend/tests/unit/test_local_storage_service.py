import asyncio
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from PIL import Image
from starlette.datastructures import Headers

from app.services.image.scanner import ProcessedImage
from app.services.storage.local import LocalStorageService


class StubScanner:
    def __init__(self, processed_image: ProcessedImage) -> None:
        self.processed_image = processed_image
        self.last_input: bytes | None = None

    def scan(self, image_bytes: bytes) -> ProcessedImage:
        self.last_input = image_bytes
        return self.processed_image


def _build_png_bytes(size: tuple[int, int], color: int) -> bytes:
    image = Image.new("L", size, color=color)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_local_storage_persists_scanned_image(tmp_path: Path) -> None:
    original_bytes = _build_png_bytes(size=(600, 900), color=180)
    scanned_bytes = _build_png_bytes(size=(420, 640), color=240)
    scanner = StubScanner(
        ProcessedImage(
            data=scanned_bytes,
            width=420,
            height=640,
            extension=".png",
        )
    )
    service = LocalStorageService(root=tmp_path / "storage", scanner=scanner)
    upload = UploadFile(
        file=BytesIO(original_bytes),
        filename="receipt.jpg",
        headers=Headers({"content-type": "image/jpeg"}),
    )

    stored = asyncio.run(
        service.save_upload(
            user_id="user/001",
            task_id="vt_123456",
            page_index=0,
            upload_file=upload,
        )
    )

    saved_path = tmp_path / "storage" / stored.path
    assert scanner.last_input == original_bytes
    assert saved_path.read_bytes() == scanned_bytes
    assert saved_path.read_bytes() != original_bytes
    assert stored.path == "user_001/tasks/vt_123456/pages/0.png"
    assert stored.width == 420
    assert stored.height == 640
    assert stored.url.endswith("/user_001/tasks/vt_123456/pages/0.png")
