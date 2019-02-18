import argparse
import glob
import json
import os
import struct
import sys

from PIL import Image

from texturelist import create_texturelist


def parse_animation(input_folder):
    animation_json = os.path.join(input_folder, "animation.json")

    if not os.path.exists(animation_json):
        print("Couldn't find animation metadata file:", animation_json)
        exit(1)

    animation_metadata = json.load(open(animation_json, "r"))

    all_images = []
    for animation in animation_metadata['animations']:
        print("Parsing", animation['label'])

        # Create sprite sheets out of images
        for image in animation['frames']:
            all_images.append(image)

    xml_data, image_info = create_texturelist(input_folder, all_images)

    for k in image_info:
        uv_rect, image_size = image_info[k]
        image_info[k] = {
            'rect':  ((0.0, 0.0), (image_size[0] - 2, 0.0), (0.0, image_size[1] - 2), (image_size[0] - 2, image_size[1] - 2)),
            'uv': (((uv_rect[0] + 1) / 1024, (uv_rect[1] + 1) / 1024), ((uv_rect[2] - 1) / 1024, (uv_rect[1] + 1) / 1024), ((uv_rect[0] + 1) / 1024, (uv_rect[3] - 1) / 1024), ((uv_rect[2] - 1) / 1024, (uv_rect[3] - 1) / 1024))
        }

    open("test.xml", "wb").write(xml_data)

    for k in image_info:
        with open("test_shape_%s.bin" % (os.path.splitext(k)[0]), "wb") as outfile:
            outfile.write("GE2D".encode('ascii'))
            outfile.write(struct.pack(">I", 0x00010000))
            outfile.write(struct.pack(">I", 0x00010100))
            outfile.write(struct.pack(">I", 0x00000098)) # Total filesize
            outfile.write(struct.pack(">I", 0x00000000))
            outfile.write(struct.pack("<HH", 1024, 1024)) # Texture sheet size
            outfile.write(struct.pack(">I", 0x00000001))
            outfile.write(struct.pack(">I", 0x00010000))

            outfile.write(struct.pack(">I", 0x0000003c)) # Rect points offset
            outfile.write(struct.pack(">I", 0x0000005c)) # Texture points offset
            outfile.write(struct.pack(">I", 0x00000000)) # Unknown offset
            outfile.write(struct.pack(">I", 0x00000034)) # Label/strings offset offset
            outfile.write(struct.pack(">I", 0x0000007c)) # Unknown data offset

            outfile.write(struct.pack(">I", 0x00000038)) # Label string offset
            outfile.write(os.path.splitext(k)[0].encode('ascii'))

            while outfile.tell() < 0x3c:
                outfile.write(struct.pack("<B", 0))

            for p in image_info[k]['rect']:
                print(p)
                outfile.write(struct.pack(">ff", *p))

            for p in image_info[k]['uv']:
                outfile.write(struct.pack(">ff", *p))

            outfile.write(struct.pack(">I", 0x040300ff))
            outfile.write(struct.pack(">I", 0x00060000))
            outfile.write(struct.pack(">I", 0x00000000))
            outfile.write(struct.pack(">I", 0x0000008c)) # Some label?

            outfile.write(struct.pack(">I", 0x00000001)) # Some label's data?
            outfile.write(struct.pack(">I", 0x00020002))
            outfile.write(struct.pack(">I", 0x00010003))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-images', help='Input images folder', required=True)
    # parser.add_argument('--output', help='Output filename', required=True)
    args = parser.parse_args()

    parse_animation(args.input_images)