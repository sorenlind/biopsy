"""Classes and functions for working with annotated slides."""
from pathlib import Path
from typing import Iterable, Optional, Tuple, Union

from openslide import OpenSlide
from PIL import Image

from .annotation import AnnotationCollection, read_ndpa
from .tile_builder import TileBuilder

JPEG_QUALITY = 80
TILE_SIZE = 512
TILE_OVERLAP = 0.0


class AnnotatedSlide:
    """OpenSlide with annotations."""

    def __init__(self, slide: OpenSlide, annotations: AnnotationCollection):
        """Initialize a new AnnotatedSlide instance.

        Args:
            slide (OpenSlide): An OpenSlide instance.
            annotations (AnnotationCollection): A collection of annotations read from an
                ndpa file.
        """
        self._slide = slide
        self._annotations = annotations

    @property
    def dimensions(self) -> Tuple[int, int]:
        """Return the dimensions of the slide.

        Returns:
            Tuple[int, int]: The dimensions.
        """
        return self._slide.dimensions

    def read_region(
        self, location: Tuple[int, int], level: int, size: Tuple[int, int]
    ) -> Tuple[Image.Image, Image.Image]:
        """Read region with top left corner at specified location.

        Args:
            location (Tuple[int, int]): The location (x, y) of top left corner of the
                region.
            level (int): The downsampling level to use. Downsampling is computed as 2 to
                the power of specified level.
            size (Tuple[int, int]): The size (width, height) of the region.

        Returns:
            Tuple[Image.Image, Image.Image]:  A tuple consisting of the slide region and
                annotation region images.
        """
        slide_region = self._slide.read_region(location, level, size).convert("RGB")

        downsample = 2 ** level
        key = f"openslide.level[{level}].downsample"
        if downsample != int(self._slide.properties[key]):
            raise ValueError("Unexpected level downsample value")

        segment_region = self._annotations.render_region(location, level, size)
        return slide_region, segment_region

    def build_tiles(
        self, level: int, tile_size: int, overlap: float, rotate: bool
    ) -> Iterable[Tuple[int, int, int, Image.Image, Image.Image]]:
        """Build tiles from the slide.

        Args:
            level (int): Zoom level
            tile_size (int): The height and width of the tiles in pixels.
            overlap (float): The fraction of overlap between each slide.
            rotate (bool): A value indicating whether to create augmentations by
                rotating the tiles.

        Returns:
            Iterable[Tuple[int, int, int, Image.Image, Image.Image]]: [description]
        """
        builder = TileBuilder(self)
        return builder.build(level, tile_size, overlap, rotate)


def read_annotated_slide(
    slide_file: Union[str, Path], annotations_file: Optional[Union[str, Path]] = None
) -> AnnotatedSlide:
    """Read specified slide file and its annotations and return annotated slide.

    Args:
        slide_file (Union[str, Path]): OpenSlide file.
        annotations_file (Optional[Union[str, Path]], optional): A ndpa annotations
            file, defaults to None. If None is specified, the annotations file is
            expected to be named identically with the slide file except for the
            extension. Defaults to None.

    Returns:
        AnnotatedSlide: An annotated slide
    """
    if isinstance(slide_file, Path):
        slide_file = str(slide_file)
    slide = OpenSlide(slide_file)

    if annotations_file is None:
        annotations_file = Path(slide_file).with_suffix(".ndpi.ndpa")

    dimensions = slide.dimensions

    mpp_x = float(slide.properties["openslide.mpp-x"])
    mpp_y = float(slide.properties["openslide.mpp-y"])

    offset_x = int(slide.properties["hamamatsu.XOffsetFromSlideCentre"])
    offset_y = int(slide.properties["hamamatsu.YOffsetFromSlideCentre"])

    annotations = read_ndpa(
        annotations_file, dimensions, (mpp_x, mpp_y), (offset_x, offset_y)
    )
    return AnnotatedSlide(slide, annotations)
