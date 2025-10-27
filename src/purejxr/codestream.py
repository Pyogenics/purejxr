"""Module to handle the JPEG XR codestream"""

from typing import BinaryIO
from dataclasses import dataclass
from enum import IntEnum

from bitstring import ConstBitStream

from ._iotools import *

"""
Exceptions
"""
class CodestreamSignatureError(Exception): pass


"""
Constants
"""
CODESTREAM_IMAGE_HEADER_SIGNATURE = b"WMPHOTO\x00"


"""
Data
"""
class CodestreamOverlapMode(IntEnum):
    """This enum specifies the overlap processing mode of the image.
    
    When overlap_mode = 0 no filtering is applied
    When overlap_mode = 1 only the second level overlap filter is applied
    When overlap_mode = 2 both first and second level overlap filters are used
    """
    NONE = 0
    SECOND_LEVEL_FILTER = 1
    FILTER_BOTH = 2
    RESERVED = 3


class CodestreamOutputColourFormat(IntEnum):
    """This enum specifies the colour format of the output image."""
    RESERVED = -1
    YONLY = 0
    YUV420 = 1
    YUV422 = 2
    YUV444 = 3
    CMYK = 4
    CMYKDIRECT = 5
    NCOMPONENT = 6
    RGB = 7
    RGBE = 8


class CodestreamOutputBitdepth(IntEnum):
    """This enum specfifies the bitdepth of the output image."""
    RESERVED = -1
    BD1WHITE1 = 0
    BD8 = 1
    BD16 = 2
    BD16S = 3
    BD16F = 4
    BD32S = 6
    BD32F = 7
    BD5 = 8
    BD10 = 9
    BD565 = 10
    BD1BLACK1 = 15


@dataclass
class CodestreamImageHeader:
    """Header of a JPEG XR codestream image"""
    reserved_b: int
    hard_tiling: bool
    reserved_c: int
    tiling: bool
    frequency_mode_layout: bool
    spatial_transform: int
    index_table_present: bool
    overlap_mode: CodestreamOverlapMode
    short_header: bool
    long_word: bool
    windowing: bool
    trim_flexbits: bool
    reserved_d: int
    red_blue_not_swapped: bool
    premultiplied_alpha: bool
    alpha_image_plane: bool
    output_colour_format: CodestreamOutputColourFormat
    output_bitdepth: CodestreamOutputBitdepth
    width: int
    height: int
    vertical_tile_count: int
    horizontal_tile_count: int
    tile_widths: list[int]
    tile_heights: list[int]
    top_margin: int
    left_margin: int
    bottom_margin: int
    right_margin: int


"""
Readers
"""
def read_image_header(stream: BinaryIO) -> CodestreamImageHeader:
    """Read and verify the image header of a JPEG XR codestream"""
    # Verify signature
    signature = stream.read(8)
    if signature != CODESTREAM_IMAGE_HEADER_SIGNATURE:
        raise CodestreamSignatureError(f"Invalid JPEG XR codestream signature: {CODESTREAM_IMAGE_HEADER_SIGNATURE}")
    
    # Read bit based data
    bit_stream = ConstBitStream(stream.read(4))
    
    reserved_b = bit_stream.read("uint:4")
    hard_tiling = bit_stream.read("bool")
    reserved_c = bit_stream.read("uint:3")
    tiling = bit_stream.read("bool")
    frequency_mode_layout = bit_stream.read("bool")
    spatial_transform = bit_stream.read("uint:3")
    index_table_present = bit_stream.read("bool")

    overlap_mode = CodestreamOverlapMode.NONE # XXX: undefined behaviour when overlap_mode is not one of the known values?
    overlap_mode_raw = bit_stream.read("uint:2")
    if overlap_mode_raw in iter(CodestreamOverlapMode):
        overlap_mode = CodestreamOverlapMode(overlap_mode_raw)

    short_header = bit_stream.read("bool")
    long_word = bit_stream.read("bool")
    windowing = bit_stream.read("bool")
    trim_flexbits = bit_stream.read("bool")
    reserved_d = bit_stream.read("uint:1")
    red_blue_not_swapped = bit_stream.read("bool")
    premultiplied_alpha = bit_stream.read("bool")
    alpha_image_plane = bit_stream.read("bool")

    output_colour_format = CodestreamOutputColourFormat.RESERVED
    output_colour_format_raw = bit_stream.read("uint:4")
    if output_colour_format_raw in iter(CodestreamOutputColourFormat):
        output_colour_format = CodestreamOutputColourFormat(output_colour_format_raw)
    
    output_bitdepth = CodestreamOutputBitdepth.RESERVED
    output_bitdepth_raw = bit_stream.read("uint:4")
    if output_bitdepth_raw in iter(CodestreamOutputBitdepth):
        output_bitdepth = CodestreamOutputBitdepth(output_bitdepth_raw)

    # Read width and height (in macro blocks)
    width = 0
    height = 0
    if short_header:
        width = read_uint16(stream) + 1
        height = read_uint16(stream) + 1
    else:
        width = read_uint32(stream) + 1
        height = read_uint32(stream) + 1
    
    # Read tile count and dimensions
    vertical_tile_count = 0
    horizontal_tile_count = 0
    if tiling:
        vertical_tile_count = read_uint12(stream) + 1
        horizontal_tile_count = read_uint12(stream) + 1
    
    tile_widths = []
    tile_heights = []
    for _ in range(vertical_tile_count):
        tile_width = 0
        if short_header:
            tile_width = read_uint8(stream)
        else:
            tile_width = read_uint16(stream)
        tile_widths.append(tile_width)
    for _ in range(horizontal_tile_count):
        tile_height = 0
        if short_header:
            tile_height = read_uint8(stream)
        else:
            tile_height = read_uint16(stream)
        tile_heights.append(tile_height)

    # Read margin info
    top_margin = 0
    left_margin = 0
    bottom_margin = 0
    right_margin = 0
    if windowing:
        bit_stream = ConstBitStream(stream.read(3))
        
        top_margin = bit_stream.read("uint:6")
        left_margin = bit_stream.read("uint:6")
        bottom_margin = bit_stream.read("uint:6")
        right_margin = bit_stream.read("uint:6")

    return CodestreamImageHeader(reserved_b, hard_tiling, reserved_c, tiling, frequency_mode_layout, spatial_transform, index_table_present, overlap_mode, short_header, long_word, windowing, trim_flexbits, reserved_d, red_blue_not_swapped, premultiplied_alpha, alpha_image_plane, output_colour_format, output_bitdepth, width, height, vertical_tile_count, horizontal_tile_count, tile_widths, tile_heights, top_margin, left_margin, bottom_margin, right_margin)

