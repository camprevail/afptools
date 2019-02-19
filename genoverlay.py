import argparse
import glob
import json
import os
import shutil
import struct
import sys
import tempfile

import ifstools

from lxml import etree, objectify
from lxml.builder import E
from PIL import Image

from texturelist import create_texturelist

# Example animation.json
# Creates a 5 frame animation, repeating a00 and a01
# {
#     "animations": [
#         {
#             "frames": [
#                 "a00.png",
#                 "a01.png",
#                 "a00.png",
#                 "a01.png",
#                 "a00.png"
#             ]
#         }
#     ]
# }



def parse_animation(input_folder, output_filename):
    animation_json = os.path.join(input_folder, "animation.json")

    if not os.path.exists(animation_json):
        print("Couldn't find animation metadata file:", animation_json)
        exit(1)

    animation_metadata = json.load(open(animation_json, "r"))

    all_images = []
    for animation_idx, animation in enumerate(animation_metadata['animations']):
        animation['label'] = "%02d" % animation_idx

        print("Parsing", animation['label'])

        # Create sprite sheets out of images
        for image in animation['frames']:
            all_images.append(image)

    texture_size, xml_data, image_info = create_texturelist(input_folder, all_images)

    for k in image_info:
        uv_rect, image_size = image_info[k]
        image_info[k] = {
            'rect':  ((0.0, 0.0), (image_size[0] - 2, 0.0), (0.0, image_size[1] - 2), (image_size[0] - 2, image_size[1] - 2)),
            'uv': (((uv_rect[0] + 1) / 1024, (uv_rect[1] + 1) / 1024), ((uv_rect[2] - 1) / 1024, (uv_rect[1] + 1) / 1024), ((uv_rect[0] + 1) / 1024, (uv_rect[3] - 1) / 1024), ((uv_rect[2] - 1) / 1024, (uv_rect[3] - 1) / 1024))
        }

    afp_info = {}
    with tempfile.TemporaryDirectory() as temp_folder:
        os.makedirs(os.path.join(temp_folder, "afp"))
        os.makedirs(os.path.join(temp_folder, "afp", "bsi"))
        os.makedirs(os.path.join(temp_folder, "geo"))
        os.makedirs(os.path.join(temp_folder, "tex"))

        with open(os.path.join(temp_folder, "c_version"), "w") as outfile:
            outfile.write("1.3.71\0")

        with open(os.path.join(temp_folder, "magic"), "w") as outfile:
            outfile.write("NGPF")

        for animation in animation_metadata['animations']:
            afp_info[animation['label']] = [5]

            # I'm not sure what the purpose of this blank frame is for, but create it anyway
            with open(os.path.join(temp_folder, "geo", "%s_shape5" % (animation['label'])), "wb") as outfile:
                outfile.write("GE2D".encode('ascii'))
                outfile.write(struct.pack(">I", 0x00010000))
                outfile.write(struct.pack(">I", 0x00010100))

                filesize_offset = outfile.tell()
                outfile.write(struct.pack(">I", 0x00000070)) # Total filesize
                outfile.write(struct.pack(">I", 0x00000000))
                outfile.write(struct.pack("<HH", texture_size[0], 0)) # Texture sheet size
                outfile.write(struct.pack(">I", 0x00000000))
                outfile.write(struct.pack(">I", 0x00010000))

                rect_point_offset = outfile.tell()
                outfile.write(struct.pack(">I", 0x00000034)) # Rect points offset
                outfile.write(struct.pack(">I", 0x00000000)) # Texture points offset
                outfile.write(struct.pack(">I", 0x00000000)) # Unknown offset
                outfile.write(struct.pack(">I", 0x00000000)) # Label/strings offset offset

                unk_data_offset = outfile.tell()
                outfile.write(struct.pack(">I", 0x00000054)) # Unknown data offset

                new_rect_point_offset = outfile.tell()
                rects = [(0.0, 0.0), (16.0, 0.0), (0.0, 16.0), (16.0, 16.0)]
                for p in rects:
                    outfile.write(struct.pack(">ff", *p))

                new_unk_data_offset = outfile.tell()
                outfile.write(struct.pack(">I", 0x0409ffff))
                outfile.write(struct.pack(">I", 0x00060000))
                outfile.write(struct.pack(">I", 0xff00ffff))
                outfile.write(struct.pack(">I", outfile.tell() + 4)) # Some offset?
                outfile.write(struct.pack(">I", 0x00000001)) # Some offset's data?
                outfile.write(struct.pack(">I", 0x00020002))
                outfile.write(struct.pack(">I", 0x00010003))

                new_filesize = outfile.tell()
                outfile.seek(filesize_offset, 0)
                outfile.write(struct.pack(">I", new_filesize))

                outfile.seek(rect_point_offset, 0)
                outfile.write(struct.pack(">I", new_rect_point_offset))

                outfile.seek(unk_data_offset, 0)
                outfile.write(struct.pack(">I", new_unk_data_offset))

            # Create a geo file for every image
            for i, image_name in enumerate(animation['frames']):
                afp_info[animation['label']].append(10 + i * 3)

                with open(os.path.join(temp_folder, "geo", "%s_shape%d" % (animation['label'], 10 + i * 3)), "wb") as outfile:
                    outfile.write("GE2D".encode('ascii'))
                    outfile.write(struct.pack(">I", 0x00010000))
                    outfile.write(struct.pack(">I", 0x00010100))

                    filesize_offset = outfile.tell()
                    outfile.write(struct.pack(">I", 0x00000098)) # Total filesize
                    outfile.write(struct.pack(">I", 0x00000000))
                    outfile.write(struct.pack("<HH", texture_size[0], texture_size[1])) # Texture sheet size
                    outfile.write(struct.pack(">I", 0x00000001))
                    outfile.write(struct.pack(">I", 0x00010000))

                    rect_point_offset = outfile.tell()
                    outfile.write(struct.pack(">I", 0x0000003c)) # Rect points offset

                    texture_point_offset = outfile.tell()
                    outfile.write(struct.pack(">I", 0x0000005c)) # Texture points offset
                    outfile.write(struct.pack(">I", 0x00000000)) # Unknown offset

                    strings_offset = outfile.tell()
                    outfile.write(struct.pack(">I", 0x00000034)) # Label/strings offset offset

                    unk_data_offset = outfile.tell()
                    outfile.write(struct.pack(">I", 0x0000007c)) # Unknown data offset

                    new_strings_offset = outfile.tell()
                    outfile.write(struct.pack(">I", outfile.tell() + 4)) # Label string offset
                    outfile.write(os.path.splitext(image_name)[0].encode('ascii'))

                    while (outfile.tell() % 4) != 0:
                        outfile.write(struct.pack("<B", 0))

                    new_rect_point_offset = outfile.tell()
                    for p in image_info[image_name]['rect']:
                        outfile.write(struct.pack(">ff", *p))

                    new_texture_point_offset = outfile.tell()
                    for p in image_info[image_name]['uv']:
                        outfile.write(struct.pack(">ff", *p))

                    new_unk_data_offset = outfile.tell()
                    outfile.write(struct.pack(">I", 0x040300ff))
                    outfile.write(struct.pack(">I", 0x00060000))
                    outfile.write(struct.pack(">I", 0x00000000))
                    outfile.write(struct.pack(">I", outfile.tell() + 4)) # Some offset?
                    outfile.write(struct.pack(">I", 0x00000001)) # Some offset's data?
                    outfile.write(struct.pack(">I", 0x00020002))
                    outfile.write(struct.pack(">I", 0x00010003))

                    new_filesize = outfile.tell()
                    outfile.seek(filesize_offset, 0)
                    outfile.write(struct.pack(">I", new_filesize))

                    outfile.seek(rect_point_offset, 0)
                    outfile.write(struct.pack(">I", new_rect_point_offset))

                    outfile.seek(texture_point_offset, 0)
                    outfile.write(struct.pack(">I", new_texture_point_offset))

                    outfile.seek(strings_offset, 0)
                    outfile.write(struct.pack(">I", new_strings_offset))

                    outfile.seek(unk_data_offset, 0)
                    outfile.write(struct.pack(">I", new_unk_data_offset))

                with open(os.path.join(temp_folder, "afp", "%s" % animation['label']), "wb") as outfile:
                    frame_count = len(animation['frames'])

                    outfile.write(struct.pack(">I", 0xc1d0b208)) # AP2
                    outfile.write(struct.pack(">I", 0)) # filesize
                    outfile.write(struct.pack(">I", 0x00020400))
                    outfile.write(struct.pack(">I", 0xc7000000))
                    outfile.write(struct.pack(">I", 0x00003001))
                    outfile.write(struct.pack(">I", 0x0000a001))
                    outfile.write(struct.pack(">I", 0x00780000))
                    outfile.write(struct.pack(">I", 0x000000ff))

                    outfile.write(struct.pack(">I", 0x03000100))
                    outfile.write(struct.pack(">I", 0x60000000))
                    outfile.write(struct.pack(">I", 0x3c000000))
                    outfile.write(struct.pack(">I", 0x48000000))

                    string_table_offset = outfile.tell()
                    outfile.write(struct.pack("<I", 0)) # string table offset
                    outfile.write(struct.pack("<I", 0x38)) # string table size
                    outfile.write(struct.pack(">I", 0x50000000))
                    outfile.write(struct.pack(">I", 0x82000400))
                    outfile.write(struct.pack(">I", 0x06000800))
                    outfile.write(struct.pack(">I", 0x03001800))
                    outfile.write(struct.pack(">I", 0x24000100))
                    outfile.write(struct.pack(">I", 0x02002400))
                    outfile.write(struct.pack(">I", 0x00000100))
                    outfile.write(struct.pack(">I", 0x02000000))
                    outfile.write(struct.pack(">I", 0x00000000))
                    outfile.write(struct.pack(">I", 0x00000000))

                    outfile.write(struct.pack(">I", 0x00000000))
                    outfile.write(struct.pack("<I", frame_count))
                    outfile.write(struct.pack("<I", frame_count + 6))
                    outfile.write(struct.pack(">I", 0x18000000))
                    outfile.write(struct.pack(">I", 0x18000000))
                    outfile.write(struct.pack("<I", (frame_count + 6) * 4))
                    outfile.write(struct.pack("<H", 0))
                    outfile.write(struct.pack("<H", (frame_count + 6) * 16))

                    for i in range(1, frame_count):
                        outfile.write(struct.pack("<I", frame_count + 6))

                    outfile.write(struct.pack(">I", 0x3400401e))
                    outfile.write(struct.pack(">I", 0x01000300))
                    outfile.write(struct.pack(">I", 0x08000000))
                    outfile.write(struct.pack(">I", 0x00000000))
                    outfile.write(struct.pack(">I", 0x01000000))
                    outfile.write(struct.pack(">I", 0x01000000))
                    outfile.write(struct.pack(">I", 0x18000000))
                    outfile.write(struct.pack(">I", 0x18000000))
                    outfile.write(struct.pack(">I", 0x1c000000))
                    outfile.write(struct.pack(">I", 0x00001000))
                    outfile.write(struct.pack(">I", 0x0c00c01f))
                    outfile.write(struct.pack(">I", 0x06000000))
                    outfile.write(struct.pack(">I", 0x00000100))
                    outfile.write(struct.pack(">I", 0x02000000))
                    outfile.write(struct.pack(">I", 0x04000021))
                    outfile.write(struct.pack(">I", 0x00000500))

                    outfile.write(struct.pack(">I", 0x3400401e))
                    outfile.write(struct.pack(">I", 0x01000600))
                    outfile.write(struct.pack(">I", 0x08000000))
                    outfile.write(struct.pack(">I", 0x00000000))
                    outfile.write(struct.pack(">I", 0x01000000))
                    outfile.write(struct.pack(">I", 0x01000000))
                    outfile.write(struct.pack(">I", 0x18000000))
                    outfile.write(struct.pack(">I", 0x18000000))
                    outfile.write(struct.pack(">I", 0x1c000000))
                    outfile.write(struct.pack(">I", 0x00001000))
                    outfile.write(struct.pack(">I", 0x0c00c01f))
                    outfile.write(struct.pack(">I", 0x06000000))

                    # First blank frame??
                    outfile.write(struct.pack(">I", 0x01000100))
                    outfile.write(struct.pack(">I", 0x05000000))

                    for i in range(0, frame_count):
                        outfile.write(struct.pack(">IH", 0x04000021, 0x0200))
                        outfile.write(struct.pack("<H", 10 + i * 3))

                    outfile.write(struct.pack("<H", 0x20 + (frame_count * 0x10) + (frame_count * 0x04)))
                    outfile.write(struct.pack(">H", 0x401e))
                    outfile.write(struct.pack(">I", 0x01008000))
                    outfile.write(struct.pack(">I", 0x08000000))
                    outfile.write(struct.pack(">I", 0x00000000))
                    outfile.write(struct.pack("<I", frame_count))
                    outfile.write(struct.pack("<I", frame_count))
                    outfile.write(struct.pack(">I", 0x18000000))
                    outfile.write(struct.pack(">I", 0x18000000))
                    outfile.write(struct.pack("<I", (frame_count + 6) * 4))

                    for i in range(0, frame_count):
                        outfile.write(struct.pack("<HH", i, 0x10))

                    for i in range(0, frame_count):
                        outfile.write(struct.pack(">I", 0x0c00c01f))
                        outfile.write(struct.pack(">I", 0x06000000 if i == 0 else 0x03000000))
                        outfile.write(struct.pack(">H", 0x0100))
                        outfile.write(struct.pack("<H", frame_count))
                        outfile.write(struct.pack("<I", 10 + i * 3))

                    outfile.write(struct.pack("<H", 0x48 + (frame_count * 4)))
                    outfile.write(struct.pack(">H", 0x401e))
                    outfile.write(struct.pack(">I", 0x01008200))
                    outfile.write(struct.pack(">I", 0x08000000))
                    outfile.write(struct.pack(">I", 0x00000000))
                    outfile.write(struct.pack("<I", frame_count))
                    outfile.write(struct.pack(">I", 0x01000000))
                    outfile.write(struct.pack(">I", 0x18000000))
                    outfile.write(struct.pack(">I", 0x18000000))
                    outfile.write(struct.pack("<I", (frame_count + 6) * 4))
                    outfile.write(struct.pack(">I", 0x00001000))

                    for i in range(1, frame_count):
                        outfile.write(struct.pack("<I", 1))

                    outfile.write(struct.pack(">I", 0x2400c01f))
                    outfile.write(struct.pack(">I", 0x06050001))
                    outfile.write(struct.pack(">H", 0x0200))
                    outfile.write(struct.pack("<H", frame_count))
                    outfile.write(struct.pack(">I", 0x80000000))
                    outfile.write(struct.pack(">I", 0x00040000))
                    outfile.write(struct.pack(">I", 0x00080000))
                    outfile.write(struct.pack(">I", 0xe00b0000))
                    outfile.write(struct.pack(">I", 0x40100000))
                    outfile.write(struct.pack(">I", 0xe00b0000))
                    outfile.write(struct.pack(">I", 0x20080000))
                    outfile.write(struct.pack(">I", 0x2400c01f))
                    outfile.write(struct.pack(">I", 0x06050001))
                    outfile.write(struct.pack(">H", 0x0200))
                    outfile.write(struct.pack("<H", frame_count))
                    outfile.write(struct.pack(">I", 0x80000000))
                    outfile.write(struct.pack(">I", 0x00040000))
                    outfile.write(struct.pack(">I", 0x00080000))
                    outfile.write(struct.pack(">I", 0xe00b0000))
                    outfile.write(struct.pack(">I", 0x40100000))
                    outfile.write(struct.pack(">I", 0xe00b0000))
                    outfile.write(struct.pack(">I", 0x20080000))

                    new_string_table_offset = outfile.tell()
                    outfile.write(struct.pack(">I", 0x00000000))
                    outfile.write("{}\0\0".format(animation['label']).encode('ascii')) # Name of afp file?
                    outfile.write("aep_mask_dummy\0\0".encode('ascii'))
                    outfile.write("aeplibset\0\0\0".encode('ascii'))
                    outfile.write("aeplib\0\0".encode('ascii'))
                    outfile.write("aep_dummy\0\0\0".encode('ascii'))

                    curlen = outfile.tell()
                    outfile.seek(0x04, 0)
                    outfile.write(struct.pack(">I", curlen))

                    outfile.seek(string_table_offset, 0)
                    outfile.write(struct.pack("<I", new_string_table_offset))

                with open(os.path.join(temp_folder, "afp", "bsi", "%s" % animation['label']), "wb") as outfile:
                    outfile.write(struct.pack(">I", 0x80400000)) # Swap 2 ints

        # Create afplist.xml
        afplist = E.afplist(
            *[E.afp(
                E.geo(
                    " ".join(["%d" % x for x in afp_info[k]]),
                    __type="u16",
                    __count="{}".format(len(afp_info[k]))
                ),
                name=k
            ) for k in afp_info]
        )


        with open(os.path.join(temp_folder, "afp", "afplist.xml"), "wb") as outfile:
            outfile.write(etree.tostring(afplist, pretty_print=True))

        # Copy all textures to tex folder and save texturelist.xml
        for filename in all_images:
            shutil.copyfile(os.path.join(input_folder, filename), os.path.join(temp_folder, "tex", filename))

        with open(os.path.join(temp_folder, "tex", "texturelist.xml"), "wb") as outfile:
            outfile.write(xml_data)

        ifs = ifstools.IFS(temp_folder)
        ifs.repack(path=output_filename, use_cache=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', help='Input images folder', required=True)
    parser.add_argument('--output', help='Output IFS file', required=True)
    args = parser.parse_args()

    parse_animation(args.input, args.output)
