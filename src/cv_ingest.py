from pathlib import Path
from typing import Dict, Tuple

from .models import Board, Coordinate, Tile


class VisionDependencyError(RuntimeError):
    pass


def _vision_dependencies():
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise VisionDependencyError(
            "Install optional vision dependencies with: pip install -r requirements-vision.txt"
        ) from exc
    return cv2, np


def extract_board_from_image(
    image_path: str | Path,
    tile_regions: Dict[Tuple[int, int], Tuple[int, int, int, int]],
    resource_colors: Dict[str, Tuple[int, int, int]],
    robber: Tuple[int, int] = (0, 0),
) -> Board:
    """Create board JSON from calibrated image regions and optional OCR.

    ``tile_regions`` maps axial coordinates to ``(x, y, width, height)`` image
    regions. Explicit color calibration makes this safer across different Catan
    editions; number OCR is attempted when pytesseract is installed.
    """
    cv2, np = _vision_dependencies()
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    palette = {name: np.array(rgb, dtype=np.float32) for name, rgb in resource_colors.items()}
    tiles = []
    for (q, r), (x, y, width, height) in tile_regions.items():
        crop = image[y:y + height, x:x + width]
        if crop.size == 0:
            raise ValueError(f"Tile region {(q, r)} is outside the image.")
        mean_rgb = crop.mean(axis=(0, 1))[::-1]
        resource = min(palette, key=lambda name: float(np.linalg.norm(mean_rgb - palette[name])))
        number = _read_number(crop, cv2)
        tiles.append(Tile(q=q, r=r, resource=resource, number=None if resource == "desert" else number))

    return Board(tiles=tiles, ports=[], robber=Coordinate(q=robber[0], r=robber[1]))


def _read_number(crop, cv2):
    try:
        import pytesseract
    except ImportError:
        return None
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    _, thresholded = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    text = pytesseract.image_to_string(thresholded, config="--psm 10").strip()
    try:
        number = int(text)
    except ValueError:
        return None
    return number if 2 <= number <= 12 else None
