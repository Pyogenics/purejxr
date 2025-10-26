"""Module to read and write .jxr format container files"""

from typing import BinaryIO, Any
from dataclasses import dataclass
from enum import IntEnum, Enum

from ._iotools import *

"""
Exceptions
"""
class JXRFileSignatureError(Exception): """Exception caused when the .jxr file stream doesn't contain the correct file signature."""
class JXRReaderFileVersionError(Exception): """Exception caused when the reader encounters a file version greater than its' max supported version."""
class JXRDuplicateIFDEntryError(Exception): """Exception caused when the reader encounters an entry with an ifd tag that has already been used."""
class JXRMissingRequiredIFDEntryError(Exception): """Exception caused when a required ifd field tag is missing from an ifd."""


"""
Constants
"""
READER_MAX_SUPPORTED_FILE_VERSION = 1
JXR_SIGNATURE = b"II\xbc"

"""
File data
"""
@dataclass
class JXRHeader:
    """.jxr file header"""
    version: int
    ifd_offset: int


class JXRFieldTag(IntEnum):
    """Identifies the data inside an ifd JXREntry"""
    RESERVED = -1 # This is a catch all for all element types not contained in this enum
    DOCUMENT_NAME = 0x010D
    IMAGE_DESCRIPTION = 0x010E
    EQUIPMENT_MAKE = 0x010F
    EQUIPMENT_MODEL = 0x0110
    PAGE_NAME = 0x011D
    PAGE_NUMBER = 0x0129
    SOFTWARE_NAME_VERSION = 0x0131
    DATE_TIME = 0x0132
    ARTIST_NAME = 0x013B
    HOST_COMPUTER = 0x013C
    COPYRIGHT_NOTICE = 0x8298
    COLOR_SPACE = 0xA001
    PIXEL_FORMAT = 0xBC01
    SPATIAL_XFRM_PRIMARY = 0xBC02
    IMAGE_TYPE = 0xBC04
    PTM_COLOR_INFO = 0xBC05
    PROFILE_LEVEL_CONTAINER = 0xBC06
    IMAGE_WIDTH = 0xBC80
    IMAGE_HEIGHT = 0xBC81
    WIDTH_RESOLUTION = 0xBC82
    HEIGHT_RESOLUTION = 0xBC3
    IMAGE_OFFSET = 0xBCC0
    IMAGE_BYTE_COUNT = 0xBCC1
    ALPHA_OFFSET = 0xBCC2
    ALPHA_BYTE_COUNT = 0xBCC3
    IMAGE_BAND_PRESENCE = 0xBCC4
    ALPHA_BAND_PRESENCE = 0xBCC5
    PADDING_DATA = 0xEA1C


class JXRElementType(IntEnum):
    """Identifies the type of data inside an ifd JXREntry"""
    RESERVED = -1 # This is a catch all for all element types not contained in this enum
    BYTE = 1
    UTF8 = 2
    USHORT = 3
    ULONG = 4
    URATIONAL = 5
    SBYTE = 6
    UNDEFINED = 7
    SSHORT = 8
    SLONG = 9
    SRATIONAL = 10
    FLOAT = 11
    DOUBLE = 12

    def get_data_size(self) -> int:
        """Return the size, in bytes, of the data type represented by this enum"""
        DATA_SIZE_LUT = {
            self.RESERVED: 0,
            self.BYTE: 1,
            self.UTF8: 1,
            self.USHORT: 2,
            self.ULONG: 4,
            self.URATIONAL: 8,
            self.SBYTE: 1,
            self.UNDEFINED: 1,
            self.SSHORT: 2,
            self.SLONG: 4,
            self.SRATIONAL: 8,
            self.FLOAT: 4,
            self.DOUBLE: 8
        }
        return DATA_SIZE_LUT[self]


@dataclass
class JXRImageFileDirectoryEntry:
    """An entry in the image file directory"""
    tag: JXRFieldTag
    element_type: JXRElementType
    element_count: int
    data: bytes

    def decode(self) -> object:
        """Decode the entry data into its' associated JXRFieldTag type"""
        pass


@dataclass
class JXRImageFileDirectory:
    """.jxr image file directory (ifd)"""
    entry_count: int
    entries: dict[JXRFieldTag, JXRImageFileDirectoryEntry]
    next_ifd_offset: int


@dataclass
class JXRFile:
    """.jxr file data"""
    header: JXRHeader
    image_file_directories: list[JXRImageFileDirectory]


"""
Data readers
"""
def read_header(stream: BinaryIO) -> JXRHeader:
    """Read and verify .jxr file header"""
    # Verify signature
    signature = stream.read(3)
    if signature != JXR_SIGNATURE:
        raise JXRFileSignatureError(f"Invalid .jxr file signature: {signature}")
    
    # Read header data
    version = read_uint8(stream)
    ifd_offset = read_uint32(stream)

    return JXRHeader(version, ifd_offset)


def read_image_file_directory_entry(stream: BinaryIO) -> JXRImageFileDirectoryEntry:
    """Read a .jxr image file directory entry"""
    # Need to ensure that the tag we read exists, otherwise set it to RESERVED and ignore
    tag = JXRFieldTag.RESERVED
    tag_raw = read_uint16(stream)
    if tag_raw in iter(JXRFieldTag):
        tag = JXRFieldTag(tag_raw)
    
    # Need to ensure that the type we read exists, otherwise set it to RESERVED and ignore
    element_type = JXRElementType.RESERVED
    element_type_raw = read_uint16(stream)
    if element_type_raw in iter(JXRElementType):
        element_type = JXRElementType(element_type_raw)
    element_count = read_uint32(stream)
    
    # if the size of the total data in bytes is smaller than 4 bytes treat the next field as the data, otherwise use it as an offset to the data 
    elements_size = element_type.get_data_size() * element_count
    data = None
    if elements_size > 4:
        data_offset = read_uint32(stream)
        stream_position = stream.tell()
        stream.seek(data_offset)
        data = stream.read(elements_size)
        stream.seek(stream_position)
    else:
        data = stream.read(4)

    return JXRImageFileDirectoryEntry(tag, element_type, element_count, data)


def read_image_file_directory(stream: BinaryIO) -> JXRImageFileDirectory:
    """Read a .jxr image file directory"""
    entry_count = read_uint16(stream)

    # Read ifd entries
    entries = {}
    for _ in range(entry_count):
        entry = read_image_file_directory_entry(stream)
        if entry.tag in entries:
            # this is undefined behaviour
            raise JXRDuplicateIFDEntryError(f"Duplicate IFD entry, this is undefined behaviour: {entry}, first occurence: {entries[entry.tag]}")
        entries[entry.tag] = entry

    # Validate this ifd contains all required tags
    for required_tag in [JXRFieldTag.PIXEL_FORMAT, JXRFieldTag.IMAGE_WIDTH, JXRFieldTag.IMAGE_HEIGHT, JXRFieldTag.IMAGE_OFFSET, JXRFieldTag.IMAGE_BYTE_COUNT]:
        if required_tag not in entries:
            raise JXRMissingRequiredIFDEntryError(f"IFD is missing a requird entry: {required_tag}, IFD entries: {entries}")

    next_ifd_offset = read_uint32(stream)
    return JXRImageFileDirectory(entry_count, entries, next_ifd_offset)


def read(stream: BinaryIO) -> JXRFile:
    """Read .jxr file data from a stream"""
    # Read header    
    header = read_header(stream)
    if header.version > READER_MAX_SUPPORTED_FILE_VERSION:
        raise JXRReaderFileVersionError(f".jxr file exceeds the reader's max supported file version: {header.version} (max: {READER_MAX_SUPPORTED_FILE_VERSION})")

    # Read ifds
    stream.seek(header.ifd_offset)

    image_file_directories = []
    ifd = read_image_file_directory(stream)
    image_file_directories.append(ifd)

    while ifd.next_ifd_offset != 0:
        ifd = read_image_file_directory(stream)
        image_file_directories.append(ifd)

    return JXRFile(header, image_file_directories)

