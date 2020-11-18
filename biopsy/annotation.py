"""Classes and functions for handling annotations."""
from pathlib import Path
from typing import List, Tuple, Union

from lxml import etree
from PIL import Image, ImageDraw


class Annotation:
    def __init__(self, pixel_points: List[Tuple[int, int]]):
        self._pixel_points = pixel_points
        self._location, self._size = self._compute_bounds()
        self._rendered = None
        self._current_level: int = -1

    @property
    def location(self) -> Tuple[int, int]:
        return self._location

    @property
    def size(self) -> Tuple[int, int]:
        return self._size

    @property
    def rendered(self) -> Image.Image:
        if not self._rendered:
            self._rendered = self._render()
        return self._rendered

    @property
    def current_level(self) -> int:
        return self._current_level

    @current_level.setter
    def current_level(self, value):
        if self._current_level == value:
            return
        self._current_level = value
        self._rendered = None

    def _compute_bounds(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        xs, ys = zip(*self._pixel_points)
        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)
        return (min_x, min_y), (max_x - min_x, max_y - min_y)

    def overlap(
        self, other_location: Tuple[int, int], other_size: Tuple[int, int]
    ) -> bool:
        (a_x_1, a_x_2), (a_y_1, a_y_2) = self._box_ranges(self._location, self._size)
        (b_x_1, b_x_2), (b_y_1, b_y_2) = self._box_ranges(other_location, other_size)
        x_ovelap = a_x_1 <= b_x_2 and b_x_1 <= a_x_2
        y_ovelap = a_y_1 <= b_y_2 and b_y_1 <= a_y_2
        return x_ovelap and y_ovelap

    @staticmethod
    def _box_ranges(
        location: Tuple[int, int], size: Tuple[int, int]
    ) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        (x, y), (width, height) = location, size
        range_x, range_y = (x, x + width), (y, y + height)
        return range_x, range_y

    def render_region(
        self, region_location: Tuple[int, int], level: int, region_size: Tuple[int, int]
    ) -> Image.Image:

        # Clear pre-rendered annotation if level has changed since last time.
        self.current_level = level

        # The region size is specified relative to the downsampled slide. We need to
        # compute the size relative to the full resolution (level 0) slide.
        downsample = 2 ** level
        region_size_level_0 = (region_size[0] * downsample, region_size[1] * downsample)

        # Find the part of the annotation that overlaps with the region.
        (ann_x_1, ann_y_1), (ann_x_2, ann_y_2) = self._a_relative_to_b(
            region_location, region_size_level_0, self.location, self.size
        )
        ann_x_1 //= downsample
        ann_y_1 //= downsample
        ann_x_2 //= downsample
        ann_y_2 //= downsample

        # Crop the annotation to get only the part that overlaps with the region.
        rendered_crop = self.rendered.crop((ann_x_1, ann_y_1, ann_x_2, ann_y_2))
        rendered_region = Image.new("RGBA", region_size, color=(0, 0, 0, 0))

        # Find the upper left corner of (the overlapping part of) the annotation inside
        # the region, using the level 0 resolution
        reg_1, _ = self._a_relative_to_b(
            self.location, self.size, region_location, region_size_level_0
        )

        # Convert the coorner coordinates to downsampled resolution.
        reg_1 = reg_1[0] // downsample, reg_1[1] // downsample

        # Paste the cropped annotation to the correct position of the region.
        rendered_region.paste(rendered_crop, reg_1, rendered_crop)
        return rendered_region

    @staticmethod
    def _a_relative_to_b(
        loc_a: Tuple[int, int],
        size_a: Tuple[int, int],
        loc_b: Tuple[int, int],
        size_b: Tuple[int, int],
    ) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        reg_x_1 = max(loc_a[0] - loc_b[0], 0)
        reg_x_2 = min(loc_a[0] - loc_b[0] + size_a[0], size_b[0])

        reg_y_1 = max(loc_a[1] - loc_b[1], 0)
        reg_y_2 = min(loc_a[1] - loc_b[1] + size_a[1], size_b[1])

        return (reg_x_1, reg_y_1), (reg_x_2, reg_y_2)

    def _render(self) -> Image.Image:
        downsample = 2 ** self.current_level
        points_box_relative = [
            ((x - self.location[0]) // downsample, (y - self.location[1]) // downsample)
            for x, y in self._pixel_points
        ]
        render_size = (self.size[0] // downsample, self.size[1] // downsample)
        temp_image = Image.new("RGBA", render_size, color=(0, 0, 0, 0),)
        x_prev, y_prev = points_box_relative[-1]
        draw_temp = ImageDraw.Draw(temp_image, "RGBA")
        for (x, y) in points_box_relative:
            draw_temp.line((x_prev, y_prev, x, y), fill=(0, 0, 0, 255), width=2)
            x_prev, y_prev = x, y

        ImageDraw.floodfill(
            temp_image, (render_size[0] / 2, render_size[1] / 2), (0, 0, 0, 255)
        )
        return temp_image

    def __repr__(self) -> str:
        return f"Annotation location {self._location}, size {self._size}"


class AnnotationCollection:
    """
    A collection of annotations relative to a slide.

    The entire collection can be rendered for a specified region of the slide.
    """

    def __init__(self, annotations: List[Annotation]):
        """
        Initialize a collection of annotations.

        :param annotations: The annotations that belong to the collection.

        :type annotations: List[Annotation]
        """
        self._annotations = annotations

    def render_region(
        self, location: Tuple[int, int], level: int, size: Tuple[int, int]
    ) -> Image.Image:
        """
        Render the annotations for specified region of the slide.

        :param location: The location of the region relative to the slide.

        :type location: Tuple[int, int]

        :param size:  The size the region.

        :type size: Tuple[int, int]

        :return: The rendered annotations.

        :rtype: Image.Image
        """
        if size[0] != size[1]:
            raise NotImplementedError("Non-square regions not implemented.")

        segment_area = Image.new(mode="RGBA", size=size, color=(0, 0, 0, 0))

        downsample = 2 ** level
        size_level_0 = (size[0] * downsample, size[1] * downsample)

        for annotation in self._annotations:
            if not annotation.overlap(location, size_level_0):
                continue
            annotation_segment = annotation.render_region(location, level, size)
            segment_area.paste(annotation_segment, (0, 0), annotation_segment)
        segment_area = segment_area.convert("LA")
        return segment_area


class AnnotationParser:
    """
    Parser for annotation files.
    """

    def __init__(
        self,
        dimensions: Tuple[int, int],
        mpp: Tuple[float, float],
        offset: Tuple[int, int],
    ):
        """
        Initialize an annotation parser instance relative to specified slide properties.

        :param dimensions: Pixel dimensions of slides (width, height).

        :type dimensions: Tuple[int, int]

        :param mpp: Slide level 0 microns per pixel (x, y).

        :type mpp: Tuple[float, float]

        :param offset: Distance from the center of the entire slide (i.e., the macro
            image) to the center of the main image, in nm (x, y).

        :type offset: Tuple[int, int]
        """
        self._dimensions = dimensions
        self._mpp = mpp
        self._offset = offset

    def parse(self, root: etree._Element) -> AnnotationCollection:
        """
        Parse XML tree and return a collection of annotations.

        :param root: The XML tree root.

        :type root: etree._Element

        :return: A collection of parsed annotations.

        :rtype: AnnotationCollection
        """
        annotations = []
        for raw_viewstate in root.findall("ndpviewstate"):
            viewstate = self._parse_viewstate(raw_viewstate)
            annotations.append(viewstate)
        collection = AnnotationCollection(annotations)
        return collection

    def _parse_viewstate(self, viewstate: etree._Element) -> Annotation:
        annotation = viewstate.find("annotation")
        is_closed = int(annotation.find("closed").text) == 1
        if not is_closed:
            raise ValueError("Expected a closed annotation!")
        raw_points = annotation.find("pointlist")
        physical_points = self._parse_pointlist(raw_points)
        pixel_points = [self._physical_point2level0(point) for point in physical_points]
        return Annotation(pixel_points)

    @staticmethod
    def _parse_pointlist(pointlist: etree._Element) -> List[Tuple[int, int]]:
        points = []
        for point in pointlist:
            assert point.tag == "point"
            x_cord = int(point.find("x").text)
            y_cord = int(point.find("y").text)
            points.append((x_cord, y_cord))
        return points

    def _physical_point2level0(self, point: Tuple[int, int]) -> Tuple[int, int]:
        x = self._physical_cord2level0(point[0], 0)
        y = self._physical_cord2level0(point[1], 1)
        return x, y

    def _physical_cord2level0(self, coord: int, dimension: int) -> int:
        temp: float = coord - self._offset[dimension]
        temp = temp / (self._mpp[dimension] * 1_000)
        temp = temp + (self._dimensions[dimension] / 2)
        return round(temp)


def read_ndpa(
    annotation_file: Union[str, Path],
    dimensions: Tuple[int, int],
    mpp: Tuple[float, float],
    offset: Tuple[int, int],
) -> AnnotationCollection:
    """
    Read annotation file and return an AnnotationCollection instance.

    The annotations are read relative to a slide with specified dimensions, mpp and
    offset.

    :param annotation_file: Path to the annotation file.

    :type annotation_file: Union[str, Path]

    :param dimensions: The dimensions of the slide (width, height).

    :type dimensions: Tuple[int, int]

    :param mpp: Slide level 0 microns per pixel (x, y).

    :type mpp: Tuple[float, float]

    :param offset: Distance from the center of the entire slide (i.e., the macro image)
        to the center of the main image, in nm (x, y).

    :type offset: Tuple[int, int]

    :return: A collection of annotations.

    :rtype: AnnotationCollection
    """
    if isinstance(annotation_file, str):
        annotation_file = Path(annotation_file)
    root = etree.parse(annotation_file.open(mode="rb")).getroot()
    annotation_parser = AnnotationParser(dimensions, mpp, offset)
    annotations = annotation_parser.parse(root)
    return annotations
