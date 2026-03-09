from __future__ import annotations

import argparse
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from pypdf import PdfReader


# Tuned for this specific 5-page photo PDF after inspection.
PAGE_CONFIG = {
    1: {"rotation": "cw", "crop": (170, 0, 1470, 848)},
    2: {"rotation": "ccw", "crop": (105, 0, 1463, 848)},
    3: {"rotation": "ccw", "crop": (120, 20, 1500, 790)},
    4: {"rotation": "ccw", "crop": (120, 20, 1500, 790)},
    5: {"rotation": "ccw", "crop": (120, 20, 1500, 790)},
}


def extract_page_images(pdf_path: Path) -> list[np.ndarray]:
    reader = PdfReader(str(pdf_path))
    images: list[np.ndarray] = []
    for index, page in enumerate(reader.pages, 1):
        page_images = list(page.images)
        if not page_images:
            raise RuntimeError(f"page {index} has no embedded image")
        data = page_images[0].data
        image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"page {index} image decode failed")
        images.append(image)
    return images


def rotate_image(image: np.ndarray, rotation: str) -> np.ndarray:
    if rotation == "cw":
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if rotation == "ccw":
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    raise ValueError(f"unsupported rotation: {rotation}")


def crop_image(image: np.ndarray, crop: tuple[int, int, int, int]) -> np.ndarray:
    x, y, w, h = crop
    return image[y : y + h, x : x + w]


def enhance_to_gray(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    background = cv2.GaussianBlur(gray, (0, 0), 35)
    normalized = cv2.divide(gray, background, scale=255)
    normalized = cv2.normalize(normalized, None, 0, 255, cv2.NORM_MINMAX)
    denoised = cv2.fastNlMeansDenoising(normalized, None, 4, 7, 21)
    softened = cv2.GaussianBlur(denoised, (0, 0), 1.0)
    enhanced = cv2.addWeighted(denoised, 1.45, softened, -0.45, 0)
    return np.clip(enhanced, 0, 255).astype(np.uint8)


def upscale_to_hd(gray: np.ndarray, target_long_edge: int) -> np.ndarray:
    height, width = gray.shape
    long_edge = max(height, width)
    if long_edge >= target_long_edge:
        return gray

    scale = target_long_edge / long_edge
    upscaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    local_contrast = cv2.createCLAHE(clipLimit=1.6, tileGridSize=(8, 8)).apply(upscaled)
    blended = cv2.addWeighted(upscaled, 0.82, local_contrast, 0.18, 0)

    stroke_mask = cv2.adaptiveThreshold(
        blended,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        31,
        10,
    )
    stroke_mask = cv2.morphologyEx(
        stroke_mask,
        cv2.MORPH_OPEN,
        np.ones((2, 2), np.uint8),
        iterations=1,
    )
    stroke_mask = cv2.dilate(stroke_mask, np.ones((2, 2), np.uint8), iterations=1)

    sharpened = cv2.addWeighted(
        blended,
        1.18,
        cv2.GaussianBlur(blended, (0, 0), 0.95),
        -0.18,
        0,
    )
    sharpened = np.clip(sharpened, 0, 255).astype(np.uint8)

    hd = sharpened.copy()
    hd[stroke_mask > 0] = np.clip(
        hd[stroke_mask > 0].astype(np.int16) - 12,
        0,
        255,
    ).astype(np.uint8)
    hd[(stroke_mask == 0) & (hd >= 246)] = 255
    return hd


def flatten_background_preserve_text(gray: np.ndarray) -> np.ndarray:
    content_mask = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        41,
        12,
    )
    content_mask = cv2.dilate(content_mask, np.ones((3, 3), np.uint8), iterations=1)

    background = cv2.GaussianBlur(gray, (0, 0), 45)
    flattened = cv2.divide(gray, background, scale=255)
    flattened = cv2.normalize(flattened, None, 0, 255, cv2.NORM_MINMAX)

    blended = cv2.addWeighted(gray, 0.35, flattened, 0.65, 0)
    blended[content_mask > 0] = np.minimum(blended[content_mask > 0], gray[content_mask > 0])
    blended[(content_mask == 0) & (blended > 238)] = 255
    return blended.astype(np.uint8)


def to_pil(gray_image: np.ndarray) -> Image.Image:
    return Image.fromarray(gray_image).convert("L")


def default_output_path(input_pdf: Path) -> Path:
    return input_pdf.with_name(f"{input_pdf.stem}-scan-gray-hd-v2.pdf")


def default_debug_dir(input_pdf: Path) -> Path:
    return input_pdf.with_name(f"{input_pdf.stem}-scan-gray-hd-v2-pages")


def save_page_image(gray: np.ndarray, page_path: Path, page_format: str) -> None:
    if page_format == "png":
        cv2.imencode(".png", gray)[1].tofile(os.fspath(page_path))
        return
    if page_format == "jpg":
        cv2.imencode(".jpg", gray, [int(cv2.IMWRITE_JPEG_QUALITY), 95])[1].tofile(
            os.fspath(page_path)
        )
        return
    raise ValueError(f"unsupported page format: {page_format}")


def process_pdf(
    input_pdf: Path,
    output_pdf: Path,
    debug_dir: Path,
    target_long_edge: int,
    pdf_resolution: float,
    page_format: str,
) -> None:
    page_images = extract_page_images(input_pdf)
    if len(page_images) != len(PAGE_CONFIG):
        raise RuntimeError(
            f"expected {len(PAGE_CONFIG)} pages for tuned config, got {len(page_images)}"
        )

    debug_dir.mkdir(parents=True, exist_ok=True)
    processed_pages: list[Image.Image] = []

    for page_no, image in enumerate(page_images, 1):
        config = PAGE_CONFIG[page_no]
        rotated = rotate_image(image, config["rotation"])
        cropped = crop_image(rotated, config["crop"])
        enhanced = enhance_to_gray(cropped)
        hd = upscale_to_hd(enhanced, target_long_edge=target_long_edge)
        hd = flatten_background_preserve_text(hd)

        page_path = debug_dir / f"page_{page_no:02d}.{page_format}"
        save_page_image(hd, page_path, page_format)
        processed_pages.append(to_pil(hd))

    first, rest = processed_pages[0], processed_pages[1:]
    first.save(
        output_pdf,
        save_all=True,
        append_images=rest,
        resolution=pdf_resolution,
        quality=95,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Turn the inspected photo-PDF into a cleaner grayscale scan PDF."
    )
    parser.add_argument("input_pdf", type=Path)
    parser.add_argument("--output-pdf", type=Path)
    parser.add_argument("--debug-dir", type=Path)
    parser.add_argument("--target-long-edge", type=int, default=3600)
    parser.add_argument("--pdf-resolution", type=float, default=320.0)
    parser.add_argument("--page-format", choices=("png", "jpg"), default="png")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_pdf = args.input_pdf
    output_pdf = args.output_pdf or default_output_path(input_pdf)
    debug_dir = args.debug_dir or default_debug_dir(input_pdf)
    process_pdf(
        input_pdf,
        output_pdf,
        debug_dir,
        target_long_edge=args.target_long_edge,
        pdf_resolution=args.pdf_resolution,
        page_format=args.page_format,
    )
    print(f"output_pdf={output_pdf}")
    print(f"debug_dir={debug_dir}")


if __name__ == "__main__":
    main()
