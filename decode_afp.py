import argparse
import struct
import os

def decode_afp_file(input_afp_filename, input_bsi_filename):
    bsi_file = bytearray(open(input_bsi_filename, "rb").read())
    afp_file = bytearray(open(input_afp_filename, "rb").read())

    # This can deobfuscate the magic bytes to read "AP2", but we should leave it alone.
    # The game can actually handle a fully unobfuscated ap2 file so long as the magic bytes are left intact and
    # an empty bsi file is provided.
    # afp_file = bytearray(struct.pack("<I", (struct.unpack(">I", afp_file[:4])[0] & 0x7f7f7f00)) + afp_file[4:])

    afp_offset = 0
    for i in range(0, len(bsi_file), 2):
        val = struct.unpack("<H", bsi_file[i:i+2])[0]

        if val == 0:
            break

        offset = (val & 0x7f) * 2
        swap_type = val >> 13
        loops = ((val >> 7) & 0x3f) + 1
        afp_offset += offset

        for j in range(loops):
            if swap_type == 0:
                offset = (offset << 8) - 100
                print("Check out swap type 0 code (unverified)")
                exit(1)
                continue

            swap_len = { 1: 2, 2: 4, 3: 8 }

            if swap_type not in swap_len:
                print("Unknown swap type")
                exit(1)

            afp_file[afp_offset:afp_offset+swap_len[swap_type]] = afp_file[afp_offset:afp_offset+swap_len[swap_type]][::-1]
            afp_offset += swap_len[swap_type]

    afp_size, unk_flag = struct.unpack("<IH", afp_file[4:10])
    string_table_offset, string_table_size = struct.unpack("<II", afp_file[0x30:0x38])

    for i in range(string_table_size):
        afp_file[string_table_offset + i] = (afp_file[string_table_offset + i] + 0x80 + (0xff * i)) & 0xff

    return afp_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('afp', help='Input AFP file')
    parser.add_argument('output', help='Output filename')
    parser.add_argument('-bsi', help="Optional path to BSI file. Default behavior looks in the afp/bsi dir.")
    args = parser.parse_args()

    if args.bsi is None:
        basename = os.path.basename(args.afp)
        dirname = os.path.dirname(args.afp)
        bsi = os.path.join(dirname, 'bsi', basename)
        if os.path.exists(bsi):
            args.bsi = bsi
        else:
            raise FileNotFoundError(f"Could not find BSI. Use -bsi [path] if it's not in the default location")
    decoded = decode_afp_file(args.afp, args.bsi)
    with open(args.output, "wb") as outfile:
        outfile.write(decoded)

    print("Saved to", args.output)