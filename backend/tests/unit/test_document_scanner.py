from io import BytesIO

import pytest
from PIL import Image

from app.services.image.scanner import OpenCVDocumentScanner

cv2 = pytest.importorskip("cv2", reason="opencv-python-headless is required for scanner tests")
np = pytest.importorskip("numpy", reason="numpy is required for scanner tests")

def test_document_scanner_outputs_portrait_png() -> None:
    canvas = np.full((900, 1200, 3), 70, dtype=np.uint8)
    document = np.array([[260, 120], [980, 180], [900, 760], [220, 700]], dtype=np.int32)
    cv2.fillConvexPoly(canvas, document, (245, 245, 245))
    cv2.polylines(canvas, [document], True, (255, 255, 255), 8)
    cv2.putText(canvas, "TOP", (420, 250), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (30, 30, 30), 6)
    for row in range(320, 660, 55):
        cv2.line(canvas, (300, row), (820, row), (40, 40, 40), 6)

    raw = Image.fromarray(canvas[:, :, ::-1])
    output = BytesIO()
    raw.save(output, format="JPEG")

    scanned = OpenCVDocumentScanner(max_edge=1600).scan(output.getvalue())
    scanned_image = Image.open(BytesIO(scanned.data))

    assert scanned.extension == ".png"
    assert scanned.data.startswith(b"\x89PNG")
    assert scanned.width == scanned_image.width
    assert scanned.height == scanned_image.height
    assert scanned.height > scanned.width
    assert scanned_image.convert("L").getbbox() is not None
