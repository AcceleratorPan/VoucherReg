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


class ScanPreprocessor:
    """图像预处理模块，集成 make_scan_version 的核心处理方法"""

    def __init__(self, target_long_edge: int = 2400) -> None:
        self.target_long_edge = target_long_edge

    def preprocess(self, image_bytes: bytes) -> ProcessedImage:
        """对上传的图片进行预处理，返回处理后的灰度高清图"""
        cv2 = self._import_dependency("cv2", install_hint="python -m pip install opencv-python-headless")
        np = self._import_dependency("numpy", install_hint="python -m pip install numpy")
        pil = self._import_dependency("PIL", install_hint="python -m pip install pillow")

        image = self._decode_image(image_bytes, cv2, np)
        # 先进行文档边界检测和透视变换
        warped = self._extract_document(image, cv2, np)
        oriented = self._ensure_upright(warped, cv2)

        # 转换为灰度并增强
        gray = self._enhance_to_gray(oriented, cv2, np)

        # 放大到高清
        hd = self._upscale_to_hd(gray, cv2, np)

        # 背景平面化，保留文字
        final = self._flatten_background_preserve_text(hd, cv2, np)

        # 编码为PNG
        encoded = self._encode_png(final, cv2)

        height, width = final.shape[:2]
        return ProcessedImage(data=encoded, width=width, height=height, extension=".png")

    @staticmethod
    def _import_dependency(module_name: str, install_hint: str) -> ModuleType:
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            raise AppException(
                status_code=500,
                code="IMAGE_PROCESSOR_DEPENDENCY_MISSING",
                message=f"{module_name} is required for image preprocessing. Install with: {install_hint}",
            ) from exc

    @staticmethod
    def _decode_image(image_bytes: bytes, cv2: ModuleType, np: ModuleType) -> Any:
        buffer = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if image is None:
            raise ValidationException(message="Uploaded file is not a valid image")
        return image

    def _extract_document(self, image: Any, cv2: ModuleType, np: ModuleType) -> Any:
        """提取文档区域（透视变换）"""
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
            # 没有找到文档边界，返回原图
            return image

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

            perimeter = cv2.arcLength(contour, True)
            approximation = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
            if len(approximation) == 4:
                polygon = approximation.reshape(4, 2).astype(np.float32)
                score = self._score_quadrilateral(polygon, area, image.shape[:2], np)
                if score > best_score:
                    best_candidate = polygon
                    best_score = score

            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect).astype(np.float32)
            score = self._score_quadrilateral(box, area, image.shape[:2], np)
            if score > best_score:
                best_candidate = box
                best_score = score

        return best_candidate

    @staticmethod
    def _score_quadrilateral(
        points: Any,
        contour_area: float,
        image_shape: tuple[int, int],
        np: ModuleType,
    ) -> float:
        ordered = ScanPreprocessor._order_corners(points=points, np=np)
        width, height = ScanPreprocessor._quadrilateral_size(points=ordered, np=np)
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
        max_width, max_height = ScanPreprocessor._quadrilateral_size(points=corners, np=np)
        max_width = max(int(round(max_width)), 1)
        max_height = max(int(round(max_height)), 1)

        destination = np.array(
            [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
            dtype=np.float32,
        )
        transform = cv2.getPerspectiveTransform(corners, destination)
        return cv2.warpPerspective(image, transform, (max_width, max_height))

    def _ensure_upright(self, image: Any, cv2: ModuleType) -> Any:
        """确保图像方向正确"""
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

    def _enhance_to_gray(self, image: Any, cv2: ModuleType, np: ModuleType) -> Any:
        """转换为灰度图并进行基础增强（来自 make_scan_version）"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        background = cv2.GaussianBlur(gray, (0, 0), 35)
        normalized = cv2.divide(gray, background, scale=255)
        normalized = cv2.normalize(normalized, None, 0, 255, cv2.NORM_MINMAX)
        denoised = cv2.fastNlMeansDenoising(normalized, None, 4, 7, 21)
        softened = cv2.GaussianBlur(denoised, (0, 0), 1.0)
        enhanced = cv2.addWeighted(denoised, 1.45, softened, -0.45, 0)
        return np.clip(enhanced, 0, 255).astype(np.uint8)

    def _upscale_to_hd(self, gray: Any, cv2: ModuleType, np: ModuleType) -> Any:
        """放大到高清并增强（来自 make_scan_version）"""
        height, width = gray.shape
        long_edge = max(height, width)

        if long_edge < self.target_long_edge:
            scale = self.target_long_edge / long_edge
            upscaled = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        else:
            upscaled = gray

        # 局部对比度增强
        local_contrast = cv2.createCLAHE(clipLimit=1.6, tileGridSize=(8, 8)).apply(upscaled)
        blended = cv2.addWeighted(upscaled, 0.82, local_contrast, 0.18, 0)

        # 笔画锐化
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

        # 应用笔画加深
        hd = sharpened.copy()
        hd[stroke_mask > 0] = np.clip(
            hd[stroke_mask > 0].astype(np.int16) - 12,
            0,
            255,
        ).astype(np.uint8)
        hd[(stroke_mask == 0) & (hd >= 246)] = 255
        return hd

    def _flatten_background_preserve_text(self, gray: Any, cv2: ModuleType, np: ModuleType) -> Any:
        """平板化背景，保留文字（来自 make_scan_version）"""
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

    @staticmethod
    def _encode_png(image: Any, cv2: ModuleType) -> bytes:
        success, buffer = cv2.imencode(".png", image)
        if not success:
            raise AppException(
                status_code=500,
                code="IMAGE_PROCESSING_FAILED",
                message="Failed to encode processed image",
            )
        return buffer.tobytes()


class HighResGrayscaleScanner:
    """高清灰度扫描器，结合文档检测和 make_scan_version 的图像增强方法"""

    def __init__(self, target_long_edge: int = 2400) -> None:
        self.target_long_edge = target_long_edge
        self._preprocessor = ScanPreprocessor(target_long_edge=target_long_edge)

    def scan(self, image_bytes: bytes) -> ProcessedImage:
        """扫描图片，返回处理后的高清灰度图"""
        if not image_bytes:
            raise ValidationException(message="Uploaded file is empty")
        return self._preprocessor.preprocess(image_bytes)
