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


def read_rect_points(infile, offset):
    if offset == 0:
        return None

    infile.seek(offset, 0)
    points = struct.unpack(">ffffffff", infile.read(0x20))

    return points


def parse_geo(input_filename):
    with open(input_filename, "rb") as infile:
        if infile.read(4) != b'GE2D':
            print("Not a GE2D geo file")
            exit(1)

        infile.seek(0x20, 0)

        offsets = struct.unpack(">IIIII", infile.read(0x14))

        if offsets[2] != 0:
            print("Found unknown offset 2 in", input_filename)
            print(offsets)
            exit(1)

        # Read filename
        filename = read_filename(infile, offsets[3])
        print(filename)

        # Read rect points
        rect_points = read_rect_points(infile, offsets[0])
        rect_points = [x * 2 for x in rect_points]
        print(rect_points)

        # Read texture points
        infile.seek(offsets[1], 0)
        text_points = struct.unpack(">ffffffff", infile.read(0x20))
        text_points = [x * 1024 * 2 for x in points2] # 1024 = texture size... TODO
        print(text_points)

        # Not sure what this is for
        infile.seek(offsets[4], 0)
        points2 = struct.unpack("<iii", infile.read(0x0c))
        print(points2)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-geo', help='Input AFP file', required=True)
    # parser.add_argument('--output', help='Output filename', required=True)
    args = parser.parse_args()

    parse_geo(args.input_geo)
