from typing import BinaryIO


"""
Integer IO
"""
def read_int32(stream: BinaryIO, endian: str = "little") -> int:
    data = stream.read(4)
    return int.from_bytes(data, endian, signed=True)


def read_uint32(stream: BinaryIO, endian: str = "little") -> int:
    data = stream.read(4)
    return int.from_bytes(data, endian, signed=False)


def read_int16(stream: BinaryIO, endian: str = "little") -> int:
    data = stream.read(2)
    return int.from_bytes(data, endian, signed=True)


def read_uint16(stream: BinaryIO, endian: str = "little") -> int:
    data = stream.read(2)
    return int.from_bytes(data, endian, signed=False)


def read_int12(stream: BinaryIO, endian: str = "little") -> int:
    data = stream.read(3)
    return int.from_bytes(data, endian, signed=True)


def read_uint12(stream: BinaryIO, endian: str = "little") -> int:
    data = stream.read(3)
    return int.from_bytes(data, endian, signed=False)


def read_int8(stream: BinaryIO) -> int:
    data = stream.read(1)
    return int.from_bytes(data, signed=True)


def read_uint8(stream: BinaryIO) -> int:
    data = stream.read(1)
    return int.from_bytes(data, signed=False)

