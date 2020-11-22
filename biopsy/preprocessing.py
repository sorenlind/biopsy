"""Preprocessing of slides."""

from pathlib import Path

from tqdm.auto import tqdm

from .annotated_slide import read_annotated_slide


def preprocess(
    input_folder: Path,
    output_folder: Path,
    level: int,
    tile_size: int,
    overlap: float,
    rotate: bool,
):
    """Create tiles and masks for all pairs of slides and annotations in a folder.

    The input folder and all its subfolders are searched.

    Args:
        input_folder (Path): Folder containing slides and annotations.
        output_folder (Path): Output folder in which to store tiles and masks.
        level (int): Zoom level.
        tile_size (int): The height and width of the tiles in pixels.
        overlap (float): The fraction of overlap between each tile.
        rotate (bool): A value indicating whether to create augmentations by
            rotating the tiles.
    """
    preprocessor = SlidePreprocessor(
        level=level, tile_size=tile_size, overlap=overlap, rotate=rotate
    )
    preprocessor.preprocess(input_folder, output_folder)


class SlidePreprocessor:
    """Class for creating tiles and masks for pairs of slides and annotations."""
    def __init__(
        self,
        level: int,
        tile_size: int,
        overlap: float,
        rotate: bool,
        jpeg_quality: int = 80,
        color_images: bool = False,
    ):
        """Initialize a SlidePreprocessor instance.

        Args:
            level (int): Zoom level.
            tile_size (int): The height and width of the tiles in pixels.
            overlap (float): The fraction of overlap between each tile.
            rotate (bool): A value indicating whether to create augmentations by
                rotating the tiles.
            jpeg_quality (int, optional): JPEG quality. Defaults to 80.
            color_images (bool, optional): A value indicating whether to output color
                images. True indicates color images and False indicates grayscale
                images. Defaults to False.
        """
        self._level = level
        self._tile_size = tile_size
        self._overlap = overlap
        self._rotate = rotate
        self._jpeg_quality = jpeg_quality
        self._color_images = color_images

    def preprocess(self, input_folder: Path, output_folder: Path):
        """Create tiles for all pairs of slides and annotations in specified folder.

        The input folder and all its subfolders are searched.

        Args:
            input_folder (Path): Folder containing slides and annotations.
            output_folder (Path): Output folder in which to store tiles and masks.
        """
        n_preprocessed = 0
        for slide_file in tqdm(list(input_folder.glob("**/*.ndpi"))):
            annotation_file = slide_file.with_suffix(".ndpi.ndpa")
            if not annotation_file.is_file():
                continue
            slide_output_folder = output_folder / slide_file.with_suffix("").name
            slide_output_folder.mkdir(exist_ok=True, parents=True)
            self._preprocess_file(slide_file, slide_output_folder)
            n_preprocessed += 1
        print(f"Preprocessed {n_preprocessed} annotated slide(s).")

    def _preprocess_file(self, slide_file: Path, output_folder: Path):
        annotated_slide = read_annotated_slide(slide_file)
        tiles = annotated_slide.build_tiles(
            self._level, self._tile_size, self._overlap, self._rotate
        )

        for x, y, degrees, tile, segment in tiles:
            tile_file = output_folder / (
                slide_file.with_suffix("").name + f"_{x}_{y}_{degrees}.jpeg"
            )

            if not self._color_images:
                tile = tile.convert("L")

            tile.save(
                tile_file, quality=self._jpeg_quality, optimize=True, progressive=False
            )

            # Extract alpha channel (which contains the actual mask) from segment.
            segment = segment.split()[-1]

            segment_file = tile_file.with_name(
                tile_file.with_suffix("").name + "_segment.jpeg"
            )
            segment.save(
                segment_file,
                quality=self._jpeg_quality,
                optimize=True,
                progressive=False,
            )
