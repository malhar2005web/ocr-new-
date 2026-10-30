import os
import shutil
import cv2
import numpy as np
from PIL import Image
import pytesseract
from typing import Dict, Any, List, Optional, Tuple
from app.core.config import settings
from app.core.logging import logger

class TesseractOCREngine:
    def __init__(self):
        self.tesseract_cmd = self._find_tesseract_binary()
        if self.tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            logger.info(f"Tesseract OCR initialized with binary: {self.tesseract_cmd}")
        else:
            logger.warning("Tesseract binary not found. Scanned image OCR will fall back to PyMuPDF text or LLM.")

    def _find_tesseract_binary(self) -> Optional[str]:
        # 1. Custom settings override
        if settings.TESSERACT_CMD and os.path.exists(settings.TESSERACT_CMD):
            return settings.TESSERACT_CMD
        
        # 2. In PATH
        in_path = shutil.which("tesseract")
        if in_path:
            return in_path
        
        # 3. Standard Windows locations
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
            os.path.expanduser(r"~\AppData\Local\Tesseract-OCR\tesseract.exe"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return None

    def preprocess_image(self, img_input: Any) -> np.ndarray:
        """
        State-of-the-art document image preprocessing:
        1. Grayscale conversion
        2. Orientation / deskew correction
        3. Bilateral noise filtering
        4. CLAHE contrast enhancement
        5. Adaptive thresholding
        """
        if isinstance(img_input, str):
            img = cv2.imread(img_input)
            if img is None:
                raise ValueError(f"Could not load image from {img_input}")
        elif isinstance(img_input, Image.Image):
            img = cv2.cvtColor(np.array(img_input), cv2.COLOR_RGB2BGR)
        elif isinstance(img_input, np.ndarray):
            img = img_input.copy()
        else:
            raise TypeError("Unsupported image input type")

        # Convert to grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img

        # Deskewing
        try:
            coords = np.column_stack(np.where(gray < 250))
            if len(coords) > 100:
                angle = cv2.minAreaRect(coords)[-1]
                if angle < -45:
                    angle = -(90 + angle)
                elif angle > 45:
                    angle = 90 - angle
                else:
                    angle = -angle
                
                if abs(angle) > 0.5 and abs(angle) < 45:
                    (h, w) = gray.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    gray = cv2.warpAffine(
                        gray, M, (w, h),
                        flags=cv2.INTER_CUBIC,
                        borderMode=cv2.BORDER_REPLICATE
                    )
        except Exception as e:
            logger.debug(f"Deskewing skipped: {e}")

        # Contrast Limited Adaptive Histogram Equalization (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Bilateral filter for noise removal while preserving sharp text edges
        filtered = cv2.bilateralFilter(enhanced, 9, 75, 75)

        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(
            filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 21, 10
        )

        return binary

    def extract_text_and_data(self, img_input: Any) -> Dict[str, Any]:
        """
        Extracts raw text, line items, and bounding box data with confidence scores.
        """
        if not self.tesseract_cmd:
            return {
                "text": "",
                "confidence": 0.0,
                "lines": [],
                "engine": "none"
            }

        try:
            processed = self.preprocess_image(img_input)
            
            # Extract detailed layout data
            data = pytesseract.image_to_data(
                processed,
                output_type=pytesseract.Output.DICT,
                config="--oem 3 --psm 6"
            )

            lines = []
            current_line = []
            current_line_num = -1
            confidences = []

            for i in range(len(data["text"])):
                w_text = data["text"][i].strip()
                conf = float(data["conf"][i])
                line_num = data["line_num"][i]

                if conf > 0:
                    confidences.append(conf)

                if w_text:
                    if line_num != current_line_num and current_line:
                        lines.append(" ".join(current_line))
                        current_line = []
                        current_line_num = line_num
                    current_line.append(w_text)

            if current_line:
                lines.append(" ".join(current_line))

            full_text = "\n".join(lines)
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

            return {
                "text": full_text,
                "confidence": round(avg_conf, 2),
                "lines": lines,
                "engine": "tesseract_v5"
            }

        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}")
            return {
                "text": "",
                "confidence": 0.0,
                "lines": [],
                "error": str(e),
                "engine": "tesseract_failed"
            }

image_ocr_engine = TesseractOCREngine()

