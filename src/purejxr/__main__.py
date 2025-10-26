from sys import argv
from .jxrfile import read, read_header

with open(argv[1], "rb") as stream:
    jxr_file = read(stream)
    print(jxr_file)
