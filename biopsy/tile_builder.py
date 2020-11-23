"""Classes and functions for building tiles from annotated slides."""
from math import ceil
from typing import TYPE_CHECKING, Iterable, Tuple, Iterator

from PIL import Image
from tqdm.auto import tqdm

if TYPE_CHECKING:
    from .annotated_slide import AnnotatedSlide

MOSTLY_WHITE_THRESHOLD = 0.70
ROTATIONS = [15, 30, 45]


class TileBuilder:
    """Clas for building tiles and masks from an annotated slide."""

    def __init__(self, slide: "AnnotatedSlide"):
        """Initialize a TileBuilder instance.

        Args:
            slide (AnnotatedSlide): The annotated slide for which to build tiles.
        """
        self._slide = slide
        self._level: int
        self._tile_size: int
        self._stride: int
        self._rotation_margin: int
        self._crop_coords: Tuple[int, int, int, int]

    def build(
        self, level: int, tile_size: int, overlap: float, rotate: bool
    ) -> Iterator[Tuple[int, int, int, Image.Image, Image.Image]]:
        """Build and return an iterator of tuples containing tiles and masks.

        Args:
            level (int): Zoom level.
            tile_size (int): The height and width of the tiles in pixels.
            overlap (float): The fraction of overlap between each tile.
            rotate (bool): A value indicating whether to create augmentations by
                rotating the tiles.

        Yields:
            Iterator[Tuple[int, int, int, Image.Image, Image.Image]]: Iterator of
            tuples. Each tuple consists of X coordinate, Y coordinate, degrees of
            rotation, the tile and the corresponding annotation mask.
        """
        self._level = level
        self._tile_size = tile_size
        self._tile_size_level_0 = tile_size * (2 ** level)
        self._stride = (tile_size - int(tile_size * overlap)) * (2 ** level)
        self._rotation_margin = int(ceil((tile_size * (0.5 ** 0.5)) - (tile_size / 2)))
        self._rotation_margin_level_0 = self._rotation_margin * (2 ** level)
        self._crop_coords = (
            self._rotation_margin,
            self._rotation_margin,
            tile_size + self._rotation_margin,
            tile_size + self._rotation_margin,
        )

        width, height = self._slide.dimensions
        for x in tqdm(range(0, width - self._tile_size_level_0 + 1, self._stride)):
            for y in range(0, height - self._tile_size_level_0 + 1, self._stride):

                tile, mask = self._slide.read_region(
                    (x, y), self._level, (self._tile_size, self._tile_size)
                )
                if self._is_mostly_white(tile, MOSTLY_WHITE_THRESHOLD):
                    continue
                yield x, y, 0, tile, mask

                if not rotate:
                    continue
                yield from self._build_rotations(x, y)

    def _build_rotations(
        self, x: int, y: int
    ) -> Iterable[Tuple[int, int, int, Image.Image, Image.Image]]:
        if not self._room_for_rotation((x, y)):
            return
        rotate_region_location = (
            x - self._rotation_margin_level_0,
            y - self._rotation_margin_level_0,
        )
        crop_size = (
            self._tile_size + 2 * self._rotation_margin,
            self._tile_size + 2 * self._rotation_margin,
        )
        tile, mask = self._slide.read_region(
            rotate_region_location, self._level, crop_size
        )

        for degrees in ROTATIONS:
            tile_rotated = tile.rotate(degrees).crop(self._crop_coords)
            mask_rotated = mask.rotate(degrees).crop(self._crop_coords)
            yield x, y, degrees, tile_rotated, mask_rotated

    @staticmethod
    def _is_mostly_white(region: Image.Image, threshold: float) -> bool:
        hist = region.split()[1].histogram()
        white_percentage = sum(hist[220:]) / sum(hist)
        return white_percentage >= threshold

    def _room_for_rotation(self, location: Tuple[int, int]) -> bool:
        x, y = location
        width, height = self._slide.dimensions
        if x - self._rotation_margin_level_0 < 0:
            return False
        elif y - self._rotation_margin_level_0 < 0:
            return False
        elif x + self._rotation_margin_level_0 + self._tile_size_level_0 > width:
            return False
        if y + self._rotation_margin_level_0 + self._tile_size_level_0 > height:
            return False
        return True
