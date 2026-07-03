# AP2_PLACE_OBJECT Vector Mask — Reverse Engineering Notes

This document records findings from reverse-engineering the AFP library DLLs to understand the
**Vector Mask** effect (`flags2 & 0x8`) inside the `AP2_PLACE_OBJECT` tag, plus the related `flags2`
fields.

> **Naming note.** This effect has historically been called a "transition" or "mask effect" (Konami /
> After Effects call these *transitions*, and they're most visibly used for linear/radial **wipes**).
> That name is misleading: the mechanism is a **vector shape** (anchor points with optional bezier
> tangent handles) that the library triangulates and applies as an animated **mask/clip** on a placed
> object — wipes are just one *use*. This doc uses **Vector Mask** for the mechanism, and keeps
> *transition* / *wipe* as search aliases. (Some function names in the IDBs still contain "transition".)

Sources analysed:
- **Museca** `afp-core.dll` (`PIX-2018073002`) This is the authoritative reference: it fully parses and renders the
  vector mask.
- **NBT** `libafp-win64.dll` (`NBT-2016111400`) — stripped/optimized build. Does **not** parse the
  vector mask at all (see [Version support](#version-support)).

> Addresses below are the load-time VAs seen during analysis and are only meaningful within each
> specific IDA database; treat them as anchors, not absolutes (ASLR/rebasing will shift them).

---

## TL;DR

- The Vector Mask (`flags2 & 0x8`) is a **custom animated vector mask** encoded as a `u32` slot
  bitmask followed by per-slot vertex-record chunks. Museca parses it; NBT ignores it.
- The mystery `unk_flags` field has **only two meaningful bits**:
  - `0x1` = coordinate **component width**: s16 (1 short) vs s32 (2 shorts).
  - `0x10` = record **shape/stride**: straight anchor-only vertex (2 components) vs. anchor + 2
    tangent handles (6 components, a bezier/curved segment).
- `flags2 & 0x40` is a **Colored Vector Mask** — the same vector format plus an indexed RGBA color
  palette (afputils previously marked this bit "UNKNOWN/UNHANDLED"). It feeds the same geometry builder
  as `0x8`.

---

## `flags2` field parsing (Museca `AfpPlay::HandlePlaceObject`)

`HandlePlaceObject` parses `flags1` fields first, then walks `flags2` bits from a stream pointer.
All of the following are parsed (NBT parses none of these except `flags2 & 0x2`):

| flags2 bit | field                | raw layout                        | applier (name in DB)             |
|-----------:|----------------------|-----------------------------------|----------------------------------|
| `0x2`      | rot_origin_z         | `s32` (÷20)                       | (inline)                         |
| `0x4`      | (unknown)            | flag only, no data                | `nullsub_1` (no-op / stubbed)    |
| `0x8`      | **vector mask**      | bitmask + slot chunks (see below) | `AfpMc_apply_vector_mask`    |
| `0x10`     | ap2_image_1          | `u32, s16, s16`                   | `AfpMc_apply_ap2_image1`         |
| `0x20`     | ap2_image_2          | `u16, s16, s16`                   | `AfpMc_apply_ap2_image2`         |
| `0x40`     | **colored vector mask** | same vector format as `0x8` + palette | `AfpMc_apply_colored_vector_mask` |

After parsing, an apply/dispatch block (gated by the `flags2` low byte) calls the per-effect appliers
on the `AfpMc` display object.

---

## Vector Mask binary format

```c
u32 slot_bitmask;          // bit i set => mask slot i is present; parsed low bit -> high bit

MaskSlot slots[];
for (slot_index = 0; slot_index < 32; slot_index++) {
    if (!(slot_bitmask & (1u << slot_index)))
        continue;

    u16 vertex_flags;      // per-slot; only bits 0x1 and 0x10 are used (others reserved)
    u16 vertex_count;      // number of path vertices in this slot

    bool coords_are_s32 = vertex_flags & 0x01;   // component width: 0 = s16, 1 = s32
    bool has_tangents   = vertex_flags & 0x10;   // 0 = straight (anchor only), 1 = anchor + 2 handles
    coord_t = coords_are_s32 ? s32 : s16;        // stored in twips -> divide by 20 for pixels

    MaskVertex verts[vertex_count];
    for (i = 0; i < vertex_count; i++) {
        verts[i].anchor = { read(coord_t)/20.0, read(coord_t)/20.0 };
        if (has_tangents) {
            verts[i].tangent_in  = { read(coord_t)/20.0, read(coord_t)/20.0 };
            verts[i].tangent_out = { read(coord_t)/20.0, read(coord_t)/20.0 };
        }
    }
    slots.append({ slot_index, vertex_flags, verts });
}
```

**Byte-size parity.** This preserves the old afputils accounting: a slot's payload is
`vertex_count * components_per_record * shorts_per_component` shorts, where
`components_per_record = (has_tangents ? 6 : 2)` and `shorts_per_component = (coords_are_s32 ? 2 : 1)` —
i.e. the original `(((unk_flags & 0x10) | 0x8) >> 2) * ((unk_flags & 1) + 1) * coord_count`. Because
`components_per_record` is always even, each slot (plus its 2-short header) is a multiple of 4 bytes, so
the stream stays dword-aligned with no explicit padding. An implementation that doesn't understand the
vector mask can still skip the whole block via the enclosing tag's length header (this is how NBT gets
away with ignoring it).

### `vertex_flags` decode

Only bits `0x1` and `0x10` are ever tested (in both the parser and the geometry builder). All other
bits are unused/reserved (preserve them for round-trip).

| bit    | name             | 0                                   | 1                                                |
|-------:|------------------|-------------------------------------|--------------------------------------------------|
| `0x1`  | `coords_are_s32` | s16 — 1 short per component         | s32 — 2 shorts per component                     |
| `0x10` | `has_tangents`   | anchor XY only (straight)           | anchor XY + 2 tangent handles (curved / bezier)  |

### Vertex record layout

Each vertex is one anchor XY pair plus, when `has_tangents`, two tangent-handle pairs; a "component" is
one signed X or Y value (width per the `0x1` bit). For the curved form (`vertex_flags & 0x10`):

```
vertex = [ anchor.x, anchor.y,        # the path vertex used for the mask mesh
           tangent_in.x,  tangent_in.y,    # bezier control handle (in)
           tangent_out.x, tangent_out.y ]  # bezier control handle (out)
```

For the straight form (`has_tangents` clear) only `anchor.x, anchor.y` is present. This mirrors an After
Effects / Photoshop vector-mask path vertex (an anchor point plus two tangent handles). All values are
twips (÷20).

This also explains the previously-puzzling "8 coord pairs but only 4 used" observation: those were
stride-6 records whose tangent handles were zero (i.e. effectively straight segments).

---

## Runtime handling (Museca)

Pipeline: **parse → apply/store → build geometry per frame → render.**

| stage        | function (name in DB)                 | notes                                                                 |
|--------------|---------------------------------------|-----------------------------------------------------------------------|
| parse        | `AfpPlay::HandlePlaceObject`          | reads bitmask + slot chunks from the tag stream                       |
| apply/store  | `AfpMc_apply_vector_mask`         | attaches an effect slot to the `AfpMc`; sizes & allocates the mesh    |
| effect slot  | `AfpMc_get_or_create_effect_slot`     | shared with ap2_image + bitmap overlays                               |
| build geom   | `AfpVectorMask_build_geometry`   | anchors→vertex buffer, tangents→extra buffer, triangulate, bbox       |
| triangulate  | `sub_...E53CC0` (unnamed)             | produces the `3*(n-2)` index mesh per slot                            |

### `AfpMc_apply_vector_mask` behaviour (the `0x8` applier)

1. `slot_count` = index of the highest set bit in the bitmask + 1 (number of slots to allocate).
2. Get/attach the object's effect slot; if the state id is unchanged, do nothing (cached);
   if it changed and this is an "update", take a light update path; otherwise (re)build.
3. **Size pass** re-walks the coords using the same chunk formula, accumulating
   `total_vertices = Σ coord_count` and `index_count = Σ 3*(n-2)` (triangulated fan/strip per slot).
4. Allocate one buffer: `align(slot_count*0x40)` per-slot headers + `total_vertices*8` vertices +
   `index_count*8*mult` indices + header; lay out per-slot `{unk_flags, coord_count, vertex_ptr,
   index_ptr}` sub-buffers.
5. Register the mesh with the render node and set `obj.flags |= 0x20000000` ("vector mask active").
6. Call `AfpVectorMask_build_geometry` to compute the current-frame geometry.

### `AfpVectorMask_build_geometry` behaviour

- Iterates the active slots (via the bitmask). For each slot it decodes `unk_flags` → stride, reads
  `coord_count` records, and:
  - writes each **anchor** XY (scaled by 1/20) to the slot's main vertex buffer (`slot+0x18`);
  - when stride 6, writes the **two tangent handles** (4 components) to a separate per-slot buffer
    (`slot+0x30`);
  - reads components as s16 or s32 per `unk_flags & 0x1`.
- Triangulates (`3*(n-2)` indices) and computes a per-slot and overall bounding box.

The `0x8` and `0x40` masks both funnel into this same builder, confirming `0x40` is a genuine second
vector-mask channel rather than an unknown field.

---

## Render-time consumption (the `type 0x55` node)

The masks are stored as **render nodes** on the `AfpMc` (attached via a generic node-attach helper).
Each node is 0x20 bytes: `byte[+9]` = subtype (`0x54` = `0x8` vector mask, `0x55` = `0x40` colored
vector mask), `word[+0x10]` = kind tag, `word[+0x12]` = class (`0x1D` for masks), `ptr[+0x18]` = the
geometry buffer.

During object rendering, the per-node dispatcher (`sub_7FF9E2E68930`) consumes the `0x40` mask like so:

```
if (obj.flags[+0x24] & 0x40000000) {           // "colored vector mask active"
    node = find node in obj list where byte[+9] == 0x55, class(word[+0x12]) == 0x1D
    if (node) {
        buf = node[+0x18];                     // the mask geometry buffer
        AfpMask_apply_color_state(buf);        // sub_7FF9E2E531C0
        AfpMask_rebuild_if_dirty(buf);         // sub_7FF9E2E532D0
    } else {
        obj.flags &= ~0x40000000;
    }
}
```

- **`AfpMask_apply_color_state`** reads `word[buf+0x20]` (a mode):
  - **mode 1**: takes the packed `u32` at `buf[+0x40][0]` — i.e. the palette entry `[0]` the `0x40`
    applier copied in under `sub_flags & 2` — unpacks its 4 bytes to 4 floats, multiplies by a `1/255`
    vector, and writes it to a global render-color state (the default mask color).
  - **mode 2**: writes an alternate set of integer params instead.
- **`AfpMask_rebuild_if_dirty`** checks `buf[+0x68]` (the stashed coords pointer); if non-null the mesh
  is dirty, so it refreshes the state id, re-reads the bitmask, and calls
  `AfpVectorMask_build_geometry` to regenerate the current-frame triangles, then runs a per-slot
  draw pass.

The per-slot draw pass inside `AfpMask_rebuild_if_dirty` walks the slots and, per slot, draws its
triangles (`sub_7FF9E2DB2290`, prim type 4). Crucially it reads **`word[slot+0x16]`** — the per-slot
**byte** written by `sub_flags & 4` — and uses it as a **color-palette index**:

```
idx   = word[slot+0x16];                 // per-slot byte
if (idx != prev_idx) {                    // state-change optimization
    packed = ((u32*)buf[+0x40])[idx];     // look up in the dword table (sub_flags & 2)
    if (packed != cached) {
        // unpack 4 bytes -> floats * (1/255) -> global mask color state
    }
}
draw slot triangles;
```

So the two extra `0x40` fields work together as an **indexed color palette**:
- `sub_flags & 2` → `buf[+0x40]` is a **table of packed-RGBA `u32` colors** (the palette).
- `sub_flags & 4` → each slot's `+0x16` is a **byte index into that palette**.

This lets the Colored Vector Mask give **different colors to different segments/slots** (a multi-colored
wipe), re-binding the mask color only when a slot's index changes. `AfpMask_apply_color_state` (mode 1)
sets the *initial/default* color from palette entry `[0]` before the per-slot loop refines it. The plain
`0x8` vector mask has geometry only — no palette, no per-slot color.

> The `0x8` (`type 0x54`) vector mask is consumed by an analogous path keyed on `obj.flags & 0x20000000`
> and subtype `0x54`; its accessor is `AfpMc_get_or_create_effect_slot` (returns `node[+0x18]`).

---

## `0x8` vs `0x40` — how the two mask channels differ

Both channels share the same vertex-record format (bitmask + `unk_flags`/`coord_count` chunks) and the
same geometry builder (`AfpVectorMask_build_geometry`, producing the `3*(n-2)` triangle mesh). But
`0x40` (`AfpMc_apply_colored_vector_mask`) is a **richer superset** of `0x8`
(`AfpMc_apply_vector_mask`):

| aspect                | `0x8` vector mask                         | `0x40` colored vector mask                                                |
|-----------------------|-------------------------------------------|---------------------------------------------------------------------------|
| applier input         | bare `bitmask` + `coords` pointer         | pointer to a **header struct** (see below)                                |
| bitmasks              | one                                       | **two** (`bitmask1` = geometry/slots, `bitmask2` = per-slot dword table)  |
| geometry build        | always                                    | **conditional** on `sub_flags & 1`                                        |
| extra per-slot dword  | —                                         | `sub_flags & 2`: copy `u32` per slot (from `bitmask2`) into `slot+0x40`   |
| extra per-slot byte   | —                                         | `sub_flags & 4`: copy a byte per slot into slot header `slot+0x16`        |
| render-node type      | `0x54`                                    | `0x55`                                                                     |
| object "active" flag  | `obj.flags |= 0x20000000`                 | `obj.flags |= 0x40000000`                                                  |
| node lookup           | type-`0x54` search                        | `AfpMc_find_colored_vector_mask_node` (type-`0x55` search)                        |
| color                 | none (geometry only)                      | indexed RGBA palette (`buf[+0x40]`) + per-slot index (`slot+0x16`)        |

So `0x8` and `0x40` are **two independent vector-mask channels** attached to the same `AfpMc` (each with
its own render node and object flag). The `0x40` header carries the color palette + per-slot color index
described in [Render-time consumption](#render-time-consumption-the-type-0x55-node).

### `0x40` header struct (pointed to by the applier's `r9` arg)

```
+0x00  u32 sub_flags     // bit0=has geometry, bit1=has color palette, bit2=has per-slot color index
+0x04  u32 bitmask1      // active slots for geometry (drives slot count)
+0x08  u32 bitmask2      // active slots for the color-palette table
+0x10  ptr coords        // vertex-record chunk data (same format as 0x8)
+0x18  ptr palette       // packed-RGBA u32 table (the sub_flags&2 per-slot dword copy)
+0x20  ptr color_index   // per-slot color-index bytes (the sub_flags&4 per-slot byte copy)
```

This matches how `HandlePlaceObject` parses `flags2 & 0x40`: it reads a `u32` (`sub_flags`), and only
when `sub_flags & 1` does it run the bitmask+chunk loop; further optional sections are gated by the
other `sub_flags` bits.

---

## Version support

| build                         | vector mask (`0x8`) | images (`0x10`/`0x20`) | colored (`0x40`) | notes                                    |
|-------------------------------|:-------------------:|:----------------------:|:----------------:|------------------------------------------|
| Museca `afp-core.dll` (2018)  | ✅ full             | ✅                     | ✅               | symboled; full parse + triangulated render |
| NBT `libafp-win64.dll` (2016) | ❌ ignored          | ❌ ignored             | ❌               | parses only `flags2 & 0x2`; skips rest via tag length |

In the NBT parser (`sub_18015F370`, "afp_place_object_parse_apply"), `flags2` is read into a register
but only bit `0x2` (anchor_z) is ever tested; bits `0x4/0x8/0x10/0x20/0x40` are never read. Trailing
mask/image data is simply skipped because the tag length header advances to the next tag. So the vector
mask is **unsupported** in that NBT build — whether NBT content ever authored it is unknown.

---

## Suggested `afpy` changes

- Model this field as a **Vector Mask** (keep "transition"/"wipe" as doc aliases for searchability).
- Rename `unk_flags` → `vertex_flags` (or similar) and document the two bits.
- Parse each record into `anchor` + optional `tangent_in` / `tangent_out` (stride 6), honoring the
  s16/s32 width bit.
- Stop raising on `flags2 & 0x40`; parse it as a Colored Vector Mask (same vector format + a `u32`
  RGBA palette and per-slot color-index bytes).
- Treat `flags2 & 0x4` as a no-op flag (the library dispatches it to a stub).
