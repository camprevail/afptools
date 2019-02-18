import argparse
import struct

def read_filename(infile, offset):
    if offset == 0:
        return None

    infile.seek(offset, 0)

    offset = struct.unpack(">I", infile.read(4))[0]
    infile.seek(offset, 0)

    filename = []
    while True:
        c = infile.read(1)

        if c == b'\0':
            break

        filename.append(c)

    return b"".join(filename).decode('shift-jis')


def parse_geo(input_filename):
    with open(input_filename, "rb") as infile:
        if infile.read(4) != b'GE2D':
            print("Not a GE2D geo file")
            exit(1)

        infile.seek(0x14, 0)
        texture_width, texture_height = struct.unpack("<HH", infile.read(4))

        infile.seek(0x20, 0)

        offsets = struct.unpack(">IIIII", infile.read(0x14))

        if offsets[2] != 0:
            print("Found unknown offset 2 in", input_filename)
            print(offsets)
            exit(1)

        print("Offsets:", ["%08x" % x for x in offsets])

        # Read layer label
        if offsets[3] != 0:
            label = read_filename(infile, offsets[3])
            print("Label: \"%s\"" % label)

        if offsets[0] != 0:
            # Read rect points
            infile.seek(offsets[0], 0)
            rect_points = struct.unpack(">ffffffff", infile.read(0x20))
            rect_points = [x * 2 for x in rect_points]
            rect_points = list(zip(rect_points[0::2], rect_points[1::2]))
            print("Rects", rect_points)

        if offsets[1] != 0:
            # Read texture points
            infile.seek(offsets[1], 0)
            text_points = struct.unpack(">ffffffff", infile.read(0x20))
            text_points = [x * texture_width * 2 for x in text_points]
            text_points = list(zip(text_points[0::2], text_points[1::2]))
            print("Texture rects", text_points)

        # Not sure what this is for
        if offsets[4] != 0:
            infile.seek(offsets[4], 0)
            points2 = struct.unpack("<iii", infile.read(0x0c))
            print("Unk", points2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-geo', help='Input AFP file', required=True)
    # parser.add_argument('--output', help='Output filename', required=True)
    args = parser.parse_args()

    parse_geo(args.input_geo)
