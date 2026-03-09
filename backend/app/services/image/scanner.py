from __future__ import annotations

import importlib
from dataclasses import dataclass
from types import ModuleType
from typing import Any, Protocol

from app.core.exceptions import AppException, ValidationException


@dataclass(frozen=True)
class ProcessedImage:
    data: bytes
    width: int
    height: int
    extension: str = ".png"


class ImageScanner(Protocol):
    def scan(self, image_bytes: bytes) -> ProcessedImage:
        ...


class OpenCVDocumentScanner:
    def __init__(self, max_edge: int = 1600) -> None:
        if max_edge < 100:
            raise ValueError("max_edge must be >= 100")
        self.max_edge = max_edge

    def scan(self, image_bytes: bytes) -> ProcessedImage:
        if not image_bytes:
            raise ValidationException(message="Uploaded file is empty")

        cv2 = self._import_dependency("cv2", install_hint="python -m pip install opencv-python-headless")
        np = self._import_dependency("numpy", install_hint="python -m pip install numpy")

        image = self._decode_image(image_bytes=image_bytes, cv2=cv2, np=np)
        resized = self._resize_by_max_edge(image=image, cv2=cv2)
        warped = self._extract_document(image=resized, cv2=cv2, np=np)
        oriented = self._ensure_upright(image=warped, cv2=cv2)
        enhanced = self._enhance_document(image=oriented, cv2=cv2, np=np)
        encoded = self._encode_png(image=enhanced, cv2=cv2)

        height, width = enhanced.shape[:2]
        return ProcessedImage(data=encoded, width=width, height=height, extension=".png")

    @staticmethod
    def _import_dependency(module_name: str, install_hint: str) -> ModuleType:
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            raise AppException(
                status_code=500,
                code="IMAGE_PROCESSOR_DEPENDENCY_MISSING",
                message=f"{module_name} is required for upload scanning. Install with: {install_hint}",
            ) from exc

    @staticmethod
    def _decode_image(image_bytes: bytes, cv2: ModuleType, np: ModuleType) -> Any:
        buffer = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if image is None:
            raise ValidationException(message="Uploaded file is not a valid image")
        return image

    def _resize_by_max_edge(self, image: Any, cv2: ModuleType) -> Any:
        height, width = image.shape[:2]
        max_side = max(height, width)
        if max_side <= 0:
            raise ValidationException(message="Uploaded file is not a valid image")

        scale = self.max_edge / float(max_side)
        if abs(scale - 1.0) < 1e-6:
            return image

        interpolation = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
        target_width = max(int(round(width * scale)), 1)
        target_height = max(int(round(height * scale)), 1)
        return cv2.resize(image, (target_width, target_height), interpolation=interpolation)

    def _extract_document(self, image: Any, cv2: ModuleType, np: ModuleType) -> Any:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        denoised = cv2.medianBlur(gray, 5)
        blurred = cv2.GaussianBlur(denoised, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        paper_mask = self._build_paper_mask(gray=blurred, cv2=cv2)

        quadrilateral = self._find_document_quadrilateral(
            candidate_map=paper_mask,
            image=image,
            cv2=cv2,
            np=np,
        )
        if quadrilateral is None:
            quadrilateral = self._find_document_quadrilateral(
                candidate_map=edges,
                image=image,
                cv2=cv2,
                np=np,
            )
        if quadrilateral is None:
            height, width = image.shape[:2]
            quadrilateral = np.array(
                [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
                dtype=np.float32,
            )

        ordered_corners = self._order_corners(points=quadrilateral, np=np)
        return self._warp_document(image=image, corners=ordered_corners, cv2=cv2, np=np)

    @staticmethod
    def _build_paper_mask(gray: Any, cv2: ModuleType) -> Any:
        _, paper_mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        return cv2.morphologyEx(paper_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    def _find_document_quadrilateral(
        self,
        candidate_map: Any,
        image: Any,
        cv2: ModuleType,
        np: ModuleType,
    ) -> Any | None:
        contours_result = cv2.findContours(candidate_map.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = contours_result[0] if len(contours_result) == 2 else contours_result[1]

        image_area = float(image.shape[0] * image.shape[1])
        min_area = image_area * 0.12
        best_candidate: Any | None = None
        best_score = 0.0

        for contour in sorted(contours, key=cv2.contourArea, reverse=True):
            area = cv2.contourArea(contour)
            if area < min_area:
                break

            for polygon in self._build_candidate_polygons(contour=contour, cv2=cv2, np=np):
                score = self._score_quadrilateral(
                    points=polygon,
                    contour_area=area,
                    image_shape=image.shape[:2],
                    np=np,
                )
                if score > best_score:
                    best_candidate = polygon
                    best_score = score

        return best_candidate

    def _build_candidate_polygons(self, contour: Any, cv2: ModuleType, np: ModuleType) -> list[Any]:
        candidates: list[Any] = []

        perimeter = cv2.arcLength(contour, True)
        approximation = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approximation) == 4:
            candidates.append(approximation.reshape(4, 2).astype(np.float32))

        rect = cv2.minAreaRect(contour)
        box = cv2.boxPoints(rect).astype(np.float32)
        candidates.append(box)

        unique_candidates: list[Any] = []
        for candidate in candidates:
            if not any(np.allclose(candidate, existing, atol=2.0) for existing in unique_candidates):
                unique_candidates.append(candidate)
        return unique_candidates

    def _score_quadrilateral(
        self,
        points: Any,
        contour_area: float,
        image_shape: tuple[int, int],
        np: ModuleType,
    ) -> float:
        ordered = self._order_corners(points=points, np=np)
        width, height = self._quadrilateral_size(points=ordered, np=np)
        if width <= 1.0 or height <= 1.0:
            return 0.0

        bounding_area = width * height
        if bounding_area <= 0:
            return 0.0

        rectangularity = min(contour_area / bounding_area, 1.0)
        if rectangularity < 0.45:
            return 0.0

        aspect_ratio = max(width, height) / max(min(width, height), 1.0)
        if aspect_ratio > 2.5:
            return 0.0

        image_height, image_width = image_shape
        x_margin = image_width * 0.02
        y_margin = image_height * 0.02
        border_touches = sum(
            1
            for x, y in ordered
            if x <= x_margin or x >= image_width - 1 - x_margin or y <= y_margin or y >= image_height - 1 - y_margin
        )
        border_penalty = max(0.7, 1.0 - border_touches * 0.06)
        return contour_area * rectangularity * border_penalty

    @staticmethod
    def _order_corners(points: Any, np: ModuleType) -> Any:
        ordered = np.zeros((4, 2), dtype=np.float32)
        point_sums = points.sum(axis=1)
        point_diffs = np.diff(points, axis=1)

        ordered[0] = points[np.argmin(point_sums)]
        ordered[2] = points[np.argmax(point_sums)]
        ordered[1] = points[np.argmin(point_diffs)]
        ordered[3] = points[np.argmax(point_diffs)]
        return ordered

    @staticmethod
    def _quadrilateral_size(points: Any, np: ModuleType) -> tuple[float, float]:
        top_left, top_right, bottom_right, bottom_left = points
        width = max(np.linalg.norm(bottom_right - bottom_left), np.linalg.norm(top_right - top_left))
        height = max(np.linalg.norm(top_right - bottom_right), np.linalg.norm(top_left - bottom_left))
        return float(width), float(height)

    @staticmethod
    def _warp_document(image: Any, corners: Any, cv2: ModuleType, np: ModuleType) -> Any:
        max_width, max_height = OpenCVDocumentScanner._quadrilateral_size(points=corners, np=np)
        max_width = max(int(round(max_width)), 1)
        max_height = max(int(round(max_height)), 1)

        destination = np.array(
            [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
            dtype=np.float32,
        )
        transform = cv2.getPerspectiveTransform(corners, destination)
        return cv2.warpPerspective(image, transform, (max_width, max_height))

    def _ensure_upright(self, image: Any, cv2: ModuleType) -> Any:
        oriented = image
        if oriented.shape[1] > oriented.shape[0]:
            oriented = cv2.rotate(oriented, cv2.ROTATE_90_CLOCKWISE)

        gray = cv2.cvtColor(oriented, cv2.COLOR_BGR2GRAY)
        ink = 255 - gray
        section_height = max(ink.shape[0] // 4, 1)
        top_ink = float(ink[:section_height, :].mean())
        bottom_ink = float(ink[-section_height:, :].mean())
        if bottom_ink > top_ink * 1.15:
            oriented = cv2.rotate(oriented, cv2.ROTATE_180)

        return oriented

    def _enhance_document(self, image: Any, cv2: ModuleType, np: ModuleType) -> Any:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        shadow_free = self._remove_shadows(gray=gray, cv2=cv2)
        denoised = cv2.fastNlMeansDenoising(shadow_free, None, 12, 7, 21)
        contrast = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(denoised)
        softened = cv2.GaussianBlur(contrast, (0, 0), 3)
        sharpened = cv2.addWeighted(contrast, 1.4, softened, -0.4, 0)

        binary = cv2.adaptiveThreshold(
            sharpened,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            41,
            11,
        )
        softened_binary = cv2.max(sharpened, binary)
        return cv2.medianBlur(softened_binary, 3)

    def _remove_shadows(self, gray: Any, cv2: ModuleType) -> Any:
        kernel_size = max(21, min(gray.shape[0], gray.shape[1]) // 20)
        if kernel_size % 2 == 0:
            kernel_size += 1
        kernel_size = min(kernel_size, 51)
        background = cv2.medianBlur(gray, kernel_size)
        return cv2.divide(gray, background, scale=255)

    @staticmethod
    def _encode_png(image: Any, cv2: ModuleType) -> bytes:
        success, buffer = cv2.imencode(".png", image)
        if not success:
            raise AppException(
                status_code=500,
                code="IMAGE_PROCESSING_FAILED",
                message="Failed to encode scanned image",
            )
        return buffer.tobytes()
