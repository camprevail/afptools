#pragma description AFP/AP2 - Konami flash animation format
#pragma magic [0? B2 D0 C1] @ 0x00

#include <std/io.pat>
#include <std/string.pat>
#include <std/mem.pat>
#include <std/core.pat>
#include <std/sys.pat>

// AFP format ported from code in https://github.com/DragonMinded/bemaniutils
fn Ap2Tag(u8 tagid) {
    // Every tag found in an AFP file. The majority of these are identical to tags
    // in the SWF file specification but are not seen in practice.
    str name = "Unknown tag id";
    match (tagid) {
        (0x0):       name = "END";
        (0x1):       name = "SHOW_FRAME";
        (0x2):       name = "DEFINE_SHAPE";
        (0x4):       name = "PLACE_OBJECT";
        (0x5):       name = "REMOVE_OBJECT";
        (0x6):       name = "DEFINE_BITS";
        (0x7):       name = "DEFINE_BUTTON";
        (0x8):       name = "JPEG_TABLES";
        (0x9):       name = "BACKGROUND_COLOR";
        (0xA):       name = "DEFINE_FONT";
        (0xB):       name = "DEFINE_TEXT";
        (0xC):       name = "DO_ACTION";
        (0xD):       name = "DEFINE_FONT_INFO";
        (0xE):       name = "DEFINE_SOUND";
        (0xF):       name = "START_SOUND";
        (0x11):      name = "DEFINE_BUTTON_SOUND";
        (0x12):      name = "SOUND_STREAM_HEAD";
        (0x13):      name = "SOUND_STREAM_BLOCK";
        (0x14):      name = "DEFINE_BITS_LOSSLESS";
        (0x15):      name = "DEFINE_BITS_JPEG2";
        (0x16):      name = "DEFINE_SHAPE2";
        (0x17):      name = "DEFINE_BUTTON_CXFORM";
        (0x18):      name = "PROTECT";
        (0x1A):      name = "PLACE_OBJECT2";
        (0x1C):      name = "REMOVE_OBJECT2";
        (0x20):      name = "DEFINE_SHAPE3";
        (0x21):      name = "DEFINE_TEXT2";
        (0x22):      name = "DEFINE_BUTTON2";
        (0x23):      name = "DEFINE_BITS_JPEG3";
        (0x24):      name = "DEFINE_BITS_LOSSLESS2";
        (0x25):      name = "DEFINE_EDIT_TEXT";
        (0x27):      name = "DEFINE_SPRITE";
        (0x2B):      name = "FRAME_LABEL";
        (0x2D):      name = "SOUND_STREAM_HEAD2";
        (0x2E):      name = "DEFINE_MORPH_SHAPE";
        (0x30):      name = "DEFINE_FONT2";
        (0x38):      name = "EXPORT_ASSETS";
        (0x39):      name = "IMPORT_ASSETS";
        (0x3B):      name = "DO_INIT_ACTION";
        (0x3C):      name = "DEFINE_VIDEO_STREAM";
        (0x3D):      name = "VIDEO_FRAME";
        (0x3E):      name = "DEFINE_FONT_INFO2";
        (0x40):      name = "ENABLE_DEBUGGER2";
        (0x41):      name = "SCRIPT_LIMITS";
        (0x42):      name = "SET_TAB_INDEX";
        (0x46):      name = "PLACE_OBJECT3";
        (0x47):      name = "IMPORT_ASSETS2";
        (0x4B):      name = "DEFINE_FONT3";
        (0x4D):      name = "METADATA";
        (0x4E):      name = "DEFINE_SCALING_GRID";
        (0x53):      name = "DEFINE_SHAPE4";
        (0x54):      name = "DEFINE_MORPH_SHAPE2";
        (0x56):      name = "SCENE_LABEL";
        (0x64):      name = "AFP_IMAGE";
        (0x65):      name = "AFP_DEFINE_SOUND";
        (0x66):      name = "AFP_SOUND_STREAM_BLOCK";
        (0x67):      name = "AFP_DEFINE_FONT";
        (0x68):      name = "AFP_DEFINE_SHAPE";
        (0x6E):      name = "AEP_PLACE_OBJECT";
        (0x78):      name = "AP2_DEFINE_FONT";
        (0x79):      name = "AP2_DEFINE_SPRITE";
        (0x7A):      name = "AP2_DO_ACTION";
        (0x7B):      name = "AP2_DEFINE_BUTTON";
        (0x7C):      name = "AP2_DEFINE_BUTTON_SOUND";
        (0x7D):      name = "AP2_DEFINE_TEXT";
        (0x7E):      name = "AP2_DEFINE_EDIT_TEXT";
        (0x7F):      name = "AP2_PLACE_OBJECT";
        (0x80):      name = "AP2_REMOVE_OBJECT";
        (0x81):      name = "AP2_START_SOUND";
        (0x82):      name = "AP2_DEFINE_MORPH_SHAPE";
        (0x83):      name = "AP2_IMAGE";
        (0x84):      name = "AP2_SHAPE";
        (0x85):      name = "AP2_SOUND";
        (0x86):      name = "AP2_VIDEO";
        (0x88):      name = "AP2_PLACE_CAMERA";
        (0x89):      name = "AP2_SCALING_GRID";
    }
    return name;
};

fn fmt_floatint(s32 fps) {
    return float(fps) / 1024.0;
};

fn hex(auto val) {
    return std::format("0x{:02x}", val);
};

fn fmt_frame(u32 frame_info) {
    u32 start_tag_offset = frame_info & 0xFFFFF;
    u32 num_tags_to_play = (frame_info >> 20) & 0xFFF;
    return std::format("Start tag index: {}, Tags to play: {}", start_tag_offset, num_tags_to_play);
};

fn fmt_tag_header(u32 data) {
    u32 tagtype = (data >> 22) & 0x3FF;
    u32 size = data & 0x3FFFFF;
    str tagname = Ap2Tag(tagtype);
    return std::format("Tag type: 0x{:02x} ({}), Size: {}", tagtype, tagname, size); 
};

fn fmt_shapename(u32 shapeid) {
    str name = std::mem::read_string(attrs.stringtable_offset + header.nameoffset, 30);
    return std::format("{}_shape{}", name, shapeid);
};

fn fmt_read_flt_div32768(s16 int) {
    return float(int) / 32768.0;
};

fn fmt_write_flt_div32768(auto int) {
    return s32(int * 32768.0);
};

fn fmt_read_flt_div1024(s32 int) {
    return float(int) / 1024.0;
};

fn fmt_write_flt_div1024(auto int) {
    return s32(int * 1024.0);
};

fn fmt_read_flt_div20(s32 int) {
    return float(int) / 20.0;
};

fn fmt_write_flt_div20(auto int) {
    return s32(int * 20.0);
};

fn fmt_blend(u8 blend) {
    if (blend == 3) {
        return "multiply";
    } else if (blend == 8) {
        return "addition";
    } else if (blend == 9 || blend == 70) {
        return "subtraction";
    } else if (blend == 13) {
        return "overlay";
    } else {
        return "normal";
    }
};

fn sprite_lookup(u16 sprite_id) {
    str string = std::format("id:{}", sprite_id);
    for (auto i = 0, i < std::core::member_count(exported_tags), i += 1) {
        if (sprite_id == exported_tags[i].asset_tag_id) {
            str name = std::mem::read_string(attrs.stringtable_offset + exported_tags[i].asset_string_offset, 30);
            string = std::format("id:{}, exported_name: {}", sprite_id, name);
            return string;
        }
    }
    return string;
};



struct AP2Header {
    char magic[4] [[comment("First byte is the version id.\nThe rest can be decoded to AP2 by reading\nwith big endian and & 0x7f7f7f00.")]]; 
    std::assert((magic[1] == 0xB2 && magic[2] == 0xD0 && magic[3] == 0xC1), "Unexpected magic bytes. Aborting.\nHas your data been decoded yet?");
    u32 length;
    u16 version;
    u16 nameoffset;
    u32 flags;
    u16 left;
    u16 right;
    u16 top;
    u16 bottom;
};
AP2Header header @ 0x00;


struct Color_u8 {
    u8 r;
    u8 g;
    u8 b;
    u8 a;
 } [[comment(std::format("r:{:.4f}, g:{:.4f}, b:{:.4f}, a:{:.4f}", (float(r)/255.0), (float(g)/255.0), (float(g)/255.0), (float(a)/255.0)))]];
 
struct Color_u8_reversed {
    u8 a;
    u8 b;
    u8 g;
    u8 r;
 } [[comment(std::format("r:{:.4f}, g:{:.4f}, b:{:.4f}, a:{:.4f}", (float(r)/255.0), (float(g)/255.0), (float(g)/255.0), (float(a)/255.0)))]];
 
struct Color_s16 {
    s16 r;
    s16 g;
    s16 b;
    s16 a;
 };
 
struct AP2Attributes {
    if (header.flags & 0x2) {
        s32 fps [[format_read("fmt_floatint")]];
    } else {
        float fps;
    }
    Color_u8 bg_color; // Seldom used by the game, especially in larger animations.
    u16 num_exported_assets;
    s16 imported_tags_count;
    u32 tags_base_offset [[format_read("hex")]];
    u32 asset_offset [[format_read("hex")]];
    u32 imported_tags_offset [[format_read("hex")]];
    u32 stringtable_offset [[format_read("hex")]];
    u32 stringtable_size;
    s32 imported_tag_initializers_offset [[format_read("hex")]];
};
AP2Attributes attrs @ 0x18;


struct ExportedTag {
    u16 asset_tag_id;
    u16 asset_string_offset;
    char asset_name[] @ attrs.stringtable_offset + asset_string_offset;
} [[comment(std::format("{}, sprite_id {}", asset_name, asset_tag_id))]];
ExportedTag exported_tags[attrs.num_exported_assets] @ attrs.asset_offset;


struct NamedTagReference {
    u16 asset_id;
    u16 asset_name_offset;
    char asset_name[] @ attrs.stringtable_offset + asset_name_offset;
};


struct ImportedTag {
    u16 swf_name_offset;
    u16 count;
    char swf_name[] @ attrs.stringtable_offset + swf_name_offset;
    NamedTagReference named_tagref[count];
};
ImportedTag imported_tags[attrs.imported_tags_count] @ attrs.imported_tags_offset;


struct FrameBytecode {
    u16 tag_id, frame;
    u32 action_bytecode_offset;
    u32 action_bytecode_length;
    if (action_bytecode_length > 0) {
        std::mem::Bytes<action_bytecode_length> @ attrs.imported_tag_initializers_offset + action_bytecode_offset [[name("Bytecode")]];
    }
};


struct ImportedTagsBaseInitializer {
    u16 unk1, count;
    FrameBytecode frame_bytecode[count];
};
ImportedTagsBaseInitializer imported_tags_bytecode @ attrs.imported_tag_initializers_offset;


struct TagsBaseHeader {
    u16 name_reference_flags; //This is 4 if there is are funcnames in the label table.
    u16 name_reference_count;
    u32 frame_count;
    u32 tags_count;
    u32 name_reference_offset;
    u32 frame_offset;
    u32 tags_offset;
    u16 funcname_count = 0;
    if (name_reference_flags == 4) {
        u16 funcname_count;
    }
};
TagsBaseHeader tags_base_header @ attrs.tags_base_offset;


struct Frame {
    u32 frame_info [[format_read("fmt_frame"), comment("start_tag_offset: The start tag index into the tag list where we should begin placing/executing tags for this frame.")]];
} [[comment(fmt_frame(frame_info))]];
Frame frames[tags_base_header.frame_count] @ attrs.tags_base_offset + tags_base_header.frame_offset;


struct Label {
    u16 frameno;
    u16 stringoffset;
    char string[] @ attrs.stringtable_offset + stringoffset;
} [[comment(std::format("\"{}\": frame {}", string, frameno))]];


struct AP2ShapeTag {
    u16 unk;
    u16 reference [[format_read("fmt_shapename")]];
} [[comment(fmt_shapename(reference))]];;


struct AP2ImageTag {
    u32 flags;
    u16 id;
    u16 stringoffset;
    char name[] @ attrs.stringtable_offset + stringoffset;
} [[comment(std::format("\"{}\" id:{}", name, id))]];


using Tag;
struct AP2SpriteTag {
    u16 sprite_flags, sprite_id;
    if (sprite_flags & 1 != 0) {
        u32 subtags_offset;
    }
    u32 current_pos = $;
    TagsBaseHeader subtags_base_header;
    Frame frames[subtags_base_header.frame_count] @ subtags_base_header.frame_offset + current_pos; // offsets are relative to the header
    Tag subtags[subtags_base_header.tags_count] @ subtags_base_header.tags_offset + current_pos;
    if (subtags_base_header.name_reference_count > 0) {
        Label labels[subtags_base_header.name_reference_count] @ subtags_base_header.name_reference_offset + current_pos;
    }
    u32 funcnames_offset = subtags_base_header.name_reference_offset + current_pos + (subtags_base_header.name_reference_count * 4);
    Label funcnames[subtags_base_header.funcname_count] @ funcnames_offset;
} [[comment(sprite_lookup(sprite_id))]];


struct AP2PlaceObjectTag {
    u32 start_pos = $;
    u32 flags1;
    u16 depth [[comment("The depth (level) that we should access objects from.")]]; 
    u16 object_id [[comment("The object ID that we should associate with this object,\nfor removal and presumably update and other uses.\nNot the same as Tag ID.")]];
    u64 flags = null;
    u64 unhandled_flags = null;
    if (flags1 & 0x80000000) {
        u32 more_flags [[comment("The data associated with these flags is not understood\nso we will skip parsing it")]];
        flags = flags1 | (more_flags << 32);
        unhandled_flags = flags & ~0x80000000;
    } else {
        flags = flags1;
        unhandled_flags = flags;
    }
    bool unrecognized_options = false;
    
    u16 src_tag_id = null;
    if (flags & 0x2) {
        // Has a shape or movie component.
        unhandled_flags &= ~0x2;
        u16 src_tag_id [[comment("Shape or movie id")]];
    }

    u16 label_id = null;
    if (flags & 0x10) {
        // Has label component.
        unhandled_flags &= ~0x10;
        u16 label_id;
    }
    
    char movie_name = null;
    if (flags & 0x20) {
        // Has movie name component.
        unhandled_flags &= ~0x20;
        u16 nameoffset;
        char movie_name[] @ attrs.stringtable_offset + nameoffset;
    }
    
    if (flags & 0x40) {
        unhandled_flags &= ~0x40;
        u16 unk3;
        unrecognized_options = true;
    }

    u8 blend = null;
    if (flags & 0x20000) {
        // Has blend component.
        unhandled_flags &= ~0x20000;
        u8 blend [[format_read("fmt_blend")]];
    }
    
    // Due to possible misalignment, we need to realign.
    std::mem::AlignTo<4>;
    
    if (flags & 0x100) {
        // Has scale component.
        unhandled_flags &= ~0x100;
        s32 matrix_a [[format_read("fmt_read_flt_div1024"), format_write("fmt_write_flt_div1024"), comment("div by 1024")]];
        s32 matrix_d [[format_read("fmt_read_flt_div1024"), format_write("fmt_write_flt_div1024"), comment("div by 1024")]];
    }
    
    if (flags & 0x200) {
        // Has rotate component.
        unhandled_flags &= ~0x200;
        s32 matrix_b [[format_read("fmt_read_flt_div1024"), format_write("fmt_write_flt_div1024"), comment("div by 1024")]];
        s32 matrix_c [[format_read("fmt_read_flt_div1024"), format_write("fmt_write_flt_div1024"), comment("div by 1024")]];
    }
    
    if (flags & 0x400) {
        // Has translate component.
        unhandled_flags &= ~0x400;
        s32 matrix_tx [[format_read("fmt_read_flt_div20"), format_write("fmt_write_flt_div20"), comment("div by 20")]];
        s32 matrix_ty [[format_read("fmt_read_flt_div20"), format_write("fmt_write_flt_div20"), comment("div by 20")]];
    }
    
    if (flags & 0x800) {
        // Multiplicative color present.
        unhandled_flags &= ~0x800;
        Color_s16 mult_color;
    }
    
    if (flags & 0x1000) {
        // Additive color present.
        unhandled_flags &= ~0x1000;
        Color_s16 add_color;
    }
    
    if (flags & 0x2000) {
        // Multiplicative color present, smaller integers.
        unhandled_flags &= ~0x2000;
        Color_u8_reversed mult_color;
    }
    
    if (flags & 0x4000) {
        // Additive color present, smaller integers.
        unhandled_flags &= ~0x4000;
        Color_u8_reversed add_color;
    }
    
    if (flags & 0x80) {
        // event bytecode
        unhandled_flags &= ~0x80;
        s32 event_flags, event_size;
        // Not bothering with event data.
        //$ += event_size - 8;
        std::mem::Bytes<event_size-8> event_bytecode;
    }
    
    if (flags & 0x10000) {
        // Unknown filter data
        unhandled_flags &= ~0x10000;
        s16 count, filter_size;
        std::print("Unknown filter data at 0x{:02x}", $);
    }
    
    if (flags & 0x1000000) {
        // Rotation origin
        unhandled_flags &= ~0x1000000;
        s32 rot_origin_x [[format_read("fmt_read_flt_div20"), format_write("fmt_write_flt_div20"), comment("div by 20")]];
        s32 rot_origin_y [[format_read("fmt_read_flt_div20"), format_write("fmt_write_flt_div20"), comment("div by 20")]];
    }
    
    if (flags & 0x200000000) {
        // Z Rotation origin
        unhandled_flags &= ~0x200000000;
        s32 rot_origin_z [[format_read("fmt_read_flt_div20"), format_write("fmt_write_flt_div20"), comment("div by 20")]];
    }
    
    if (flags & 0x2000000) {
        // Initialize all rotation origin to 0
        unhandled_flags &= ~0x2000000;
    }
    
    if (flags & 0x40000) {
        //This appears in newer IIDX to be an alternative method for populating
        // transform scaling. Also appears in museca.
        unhandled_flags &= ~0x40000;
        if (($ - start_pos) < parent.size) {
            s16 matrix_a [[format_read("fmt_read_flt_div32768"), format_write("fmt_write_flt_div32768"), comment("div by 32768")]];
            s16 matrix_d [[format_read("fmt_read_flt_div32768"), format_write("fmt_write_flt_div32768"), comment("div by 32768")]];
        }
    }
    
    if (flags & 0x80000) {
        // Alternative method transform rotation.
        unhandled_flags &= ~0x80000;
        s16 matrix_b [[format_read("fmt_read_flt_div32768"), format_write("fmt_write_flt_div32768"), comment("div by 32768")]];
        s16 matrix_c [[format_read("fmt_read_flt_div32768"), format_write("fmt_write_flt_div32768"), comment("div by 32768")]];
    }
    
    str shape_cmt = "";
    if (movie_name) {
        shape_cmt = std::format("movie:{} ", movie_name);
    } else if (src_tag_id) {
        shape_cmt = std::format("shape_{} ", src_tag_id);
    }
    
    str update_cmt = "";
    if (flags & 0x1) {
        unhandled_flags &= ~0x1;
        update_cmt = "Update=true";
    }
    // Not bothering with the rest of the flags. Most of the important ones are covered.
    unhandled_flags &= ~0x400000D;
    if (unhandled_flags) {
        //std::print("unhandled flags at 0x{:02x}: flags 0x{:02x}", $, unhandled_flags);
    }
    
} [[comment(std::format("d:{} id:{}, {}{}", depth, object_id, shape_cmt, update_cmt))]];


struct AP2RemoveObjectTag {
    u16 object_id, depth;
} [[comment(std::format("d:{} id:{}", depth, object_id))]];


struct Tag {
    u32 tag_header [[format_read("fmt_tag_header")]];
    str tagtype = Ap2Tag((tag_header >> 22) & 0x3FF);
    u32 size = tag_header & 0x3FFFFF;
    u32 endpos = $ + size;
    u32 curpos = $;
    
    str comment2 = "";
    if (tagtype == "AP2_SHAPE") {
        if (size != 4) {
            std::print("Invalid shape size {}", size);
        }
        AP2ShapeTag tag_SHAPE;
        str shapename = fmt_shapename(tag_SHAPE.reference);
        comment2 = std::format("id:{}, {}", tag_SHAPE.reference, shapename);
    }
    else if (tagtype == "AP2_DEFINE_SPRITE") {
        AP2SpriteTag tag_SPRITE;
        $ = curpos + size;
        comment2 = sprite_lookup(tag_SPRITE.sprite_id);
    }
    else if (tagtype == "AP2_PLACE_OBJECT") {
        AP2PlaceObjectTag tag_PLACE_OBJECT;
        if ($ < endpos) {
            $ += (endpos - $); // catchup if we didn't handle all the bytes
        }
        if (tag_PLACE_OBJECT.movie_name) {
            comment2 = std::format("d:{} id:{} srcid:{} movie:{}", tag_PLACE_OBJECT.depth, tag_PLACE_OBJECT.object_id, tag_PLACE_OBJECT.src_tag_id, tag_PLACE_OBJECT.movie_name);
        } else if (tag_PLACE_OBJECT.src_tag_id) {
            comment2 = std::format("d:{} id:{} srcid:{}", tag_PLACE_OBJECT.depth, tag_PLACE_OBJECT.object_id, tag_PLACE_OBJECT.src_tag_id);
        } else {
            comment2 = std::format("d:{} id:{}", tag_PLACE_OBJECT.depth, tag_PLACE_OBJECT.object_id);
        }
    }
    else if (tagtype == "AP2_DO_ACTION") {
        std::mem::Bytes<size> bytecode_data;
        $ = curpos + size;
    }
    else if (tagtype == "AP2_REMOVE_OBJECT") {
        AP2RemoveObjectTag tag_REMOVE_OBJECT;
        comment2 = std::format("d:{} id:{}", tag_REMOVE_OBJECT.depth, tag_REMOVE_OBJECT.object_id);
    }
    else if (tagtype == "AP2_IMAGE") {
        AP2ImageTag tag_IMAGE;
        comment2 = std::format("id:{} {}", tag_IMAGE.id, tag_IMAGE.name);
    }
    else {
        std::print("Not handling tagtype {} at 0x{:02x}", tagtype, $);
        std::mem::Bytes<(size + 3) & 0xFFFFFFFC> tag_data;
    }
} [[comment(std::format("{} {}", tagtype, comment2))]];

Tag tags[tags_base_header.tags_count] @ attrs.tags_base_offset + tags_base_header.tags_offset;

Label labels[tags_base_header.name_reference_count] @ attrs.tags_base_offset + tags_base_header.name_reference_offset;

u32 funcnames_offset = attrs.tags_base_offset + tags_base_header.name_reference_offset + (tags_base_header.name_reference_count * 4);
Label funcnames[tags_base_header.funcname_count] @ funcnames_offset;