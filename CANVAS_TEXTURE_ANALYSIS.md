# Canvas Texture (Sprite Sheet) Generation Analysis

An analysis of how the canvas textures / sprite sheets in the `pix_*_ifs` folders are
constructed, based on the `tex/texturelist.xml` manifest in each folder.

## What these are

Each `pix_*_ifs` folder is an extracted Konami **IFS** archive (BEMANI/arcade game data;
the `gf` / `grafica` naming points to *MUSECA*). The sprite-sheet system is Konami's
**AFP / texturelist** format.  

The manifest is at `tex/texturelist.xml` The `afp/` folder holds the animation/timeline 
data that *references* these textures. The `tex/` folder holds the textures that ifstools 
extracted from the sprite sheet. The `geo/` folder holds shape files that also have binary data relating to the uvrects in the texturelist. 

Inside each folder:

| Item | Purpose |
|------|---------|
| `_canvas_texNNN.png` | The generated sprite sheets (atlases) |
| `tex/texturelist.xml` | The manifest describing how each atlas is cut up |
| `tex/<name>.png` | The individual source sprites (one per `<image>`) |

## The rules behind atlas generation

There is a consistent algorithm. Every fact below was verified across **47 folders /
477 textures / 21,368 coordinates** (the original 16 folders plus the 31 in `additional/`).

### 1. One `<texture>` per canvas PNG
`<texture name="texNNN">` maps 1:1 to `_canvas_texNNN.png`. The declared `<size>` equals
the actual PNG dimensions in every case.

### 2. Coordinates are in 2× pixel units
Every coordinate in the file is even (0 odd out of 6,728). Divide by 2 to get real
pixels. This gives the UV sampler sub-pixel precision.

### 3. Two rects per sprite
- `imgrect` = the sprite's **cell** on the canvas, including its gutter.
- `uvrect` = the actual pixels sampled, **inset by exactly 1px** on the left/top, and
  1px or 3px on the right/bottom.

The **left and top gutter is always exactly 1px** (raw value `2` in 2× units, with zero
exceptions across all 21k coordinates). The **right and bottom gutter is variable: 1–4px**.

In other words: **a guaranteed 1px transparent border on the left/top of every sprite** (to
stop bilinear-filter bleed), plus extra slack on the right/bottom (most commonly +1px or
+3px, but up to +4px) used to round the cell up and absorb packer alignment. The most
common case by far is a uniform 1px border all around (`(1,1,1,1)` ≈ 75% of sprites).

> Correction from the first pass: the right/bottom gutter is **not** limited to 1px or 3px.
> The larger sample shows the full 1–4px range.

### 4. Canvas = tight bounding box of its packed sprites (not power-of-two)
The maximum `imgrect` extent exactly equals the canvas size in all 477 textures (0
mismatches). That is why dimensions are oddities like `1022×2016`, `722×1786`,
`1002×1002` rather than `1024×2048`.

The size caps are **asymmetric**: across all 477 textures, **width never exceeds 2048**,
but **height goes up to ~4096** (the tallest observed is `pix_prologue` tex000 at
`1024×4080`). This means the packer fills within a fixed maximum width and grows
*downward*, only spilling to a new canvas when it would exceed ~4096px tall.

> Correction from the first pass: the cap is **not** a symmetric 2048×2048. Width is
> capped at 2048; height can reach roughly 4096.

### 5. Packing is a largest-first rectangle bin-packer (MaxRects / guillotine style)
Not shelves. In multi-image textures the first `<image>` is the largest by area 83/86
times. The biggest sprite lands at the top-left origin, then smaller sprites fill the
subdivided free space around it.

Example — `pix_common` `tex000`: a `724×1136` sprite owns the left column, everything else
packs into the right gutter column and the strip below it.

### 6. Spill rule for splitting across canvases
Sprites are packed into `tex000` until they won't fit under the 2048 cap, then spill into
`tex001`, `tex002`, … This produces the shape seen everywhere: `tex000` is a big dense
atlas with many images, and the trailing indices degrade into single-image canvases sized
to one sprite.

Example — `pix_campaign_10`: `tex000` = 17 images @ `1022×2016`, while `tex002`–`tex011`
hold 1 image each @ `1002×1002`.

### 7. Pixel format is chosen per-texture, not per-archive
The two formats in use are `argb8888rev` (uncompressed 32-bit) and `dxt5` (block
compression). Roughly 60% of textures are `argb8888rev` and 40% `dxt5` across the full set.

Most archives happen to use a single format, but this is **not** a rule — `pix_tutorial`
and `pix_play_ready_ex` mix both within one archive. The pattern is that the large packed
atlases are usually `dxt5` (to save memory), while small textures and ones needing crisp
alpha/edges (text, line art) stay `argb8888rev`. For example `pix_play_ready_ex` keeps its
three big atlases as `dxt5` but its tiny `52×62` texture as `argb8888rev`.

Other attributes are constant everywhere: `nearest` filtering, `clamp` wrapping on both
axes, and `compress="avslz"` (AVS LZ) on the texturelist itself.

> Correction from the first pass: format is selected **per-texture** (driven by size/content),
> not uniformly per archive. `dxt5` is common, not a `pix_common`-only exception.

## The one deliberate exception: icon grids

When all items in a set are the same size, a **fixed grid** is used instead of the
bin-packer. This is not a one-off — it shows up consistently for icon/jacket sets:

- `pix_grafica_icon`, `pix_grafica_icon2`, `pix_jk_s`, `pix_jk_s_2`: every canvas is
  **404×404 holding a 2×2 grid of 202×202 song-jacket icons** (200×200 art + 1px gutter),
  with the final canvas holding the remainder (a partial row, e.g. `404×202` = 2 icons, or
  a single icon).
- `pix_rank_icon`: uniform icons again, but two different cell sizes (`122×122` and
  `52×52`), each size grouped into its own canvas.

So the general rule is: **uniform-size items are grouped by size and laid out in a regular
grid; mixed-size items go through the largest-first bin-packer.**

## Why `dxt5` for some textures and `argb8888rev` for others

`dxt5` is lossy block compression that uses ~¼ the memory of uncompressed 32-bit
`argb8888rev`. The choice between them comes down to two factors.

### Factor 1 — image content: quality vs. memory (the main driver)

DXT5 visibly mangles smooth gradients and fine color detail, but its artifacts are
invisible on flat, low-color art. So the pipeline keeps **color-rich content lossless
(`argb8888rev`)** and **compresses flat/simple content (`dxt5`)** to save memory.

The clearest evidence is `pix_tutorial`, where a single generator run produced both formats:

| Format | images | median unique colors |
|--------|--------|----------------------|
| `dxt5` | 79 | **202** |
| `argb8888rev` | 9 | **7,085** |

The ARGB images are the rich illustrations (`tut_illil_*`, gradient-heavy
`tut_serif_answer_*` at 5000+ colors); the DXT5 images are flat art, masks, and simple
text (`tut_spot_black03` = 3 colors). This is *opposite* to the naive "DXT for photos"
intuition — precisely because DXT would ruin the photographic content.

This also explains the whole-archive tendencies: illustration / jacket / story archives
(`pix_jk_s`, `pix_story`, `pix_info`) are entirely `argb8888rev`, while flat effect/text
archives (`pix_play_msg`, `pix_play_clear`, `pix_prologue`) are entirely `dxt5`. Memory is
why it's worth doing on the big atlases: DXT5 textures skew large (median area ~929k px vs
~341k for ARGB), where the 4× saving matters most.

### Factor 2 — the DXT5 "multiple of 4" constraint (a hard gate)

DXT5 compresses in 4×4 pixel blocks, so **both canvas dimensions must be divisible by 4**:

- All **100/100** DXT5 canvases are divisible by 4 in both dimensions, no exceptions.
- Because canvases are tight bounding boxes, dimensions frequently land off a multiple of 4
  (218 of 377 ARGB canvases). Those literally **cannot** be DXT5 without padding.

This is why `pix_play_ready_ex` stores a tiny `52×62`, 3-color sprite as ARGB despite it
being trivially simple: `62` isn't a multiple of 4, and padding a one-off small texture
isn't worth it, so it falls back to ARGB.

### How they combine

Content quality sets the *preference*; the multiple-of-4 rule is a hard gate that can force
ARGB for small/oddly-sized canvases. That the choice is primarily a deliberate quality call
(not just the block constraint) is confirmed by the **159 ARGB canvases that *are*
divisible by 4** — they were DXT5-eligible but kept lossless anyway.

## Summary

The generator is a standard texture-atlas baker run per-IFS with these settings:

- 2× sub-pixel coordinates
- 1px bleed-guard gutter on left/top, +1–4px slack on right/bottom (even-rounded cells)
- largest-first rectangle packing
- tight-bounding-box canvases, capped at **2048 wide × ~4096 tall**
- oversized/leftover sprites spilled into their own canvases
- pixel format chosen per-texture (`dxt5` for big atlases, `argb8888rev` for small/crisp ones)

…except uniform-size icon/jacket sets, which are grouped by size and laid out in fixed grids
(typically 2×2 of 202×202).

## What the additional samples changed

Validating against the 31 extra archives **confirmed the core algorithm** (2× coords, 1px
left/top gutter, tight-bounding-box canvases, largest-first packing, the spill rule — all
held with zero exceptions). Three details were refined:

| Claim (first pass) | Corrected finding |
|--------------------|-------------------|
| Right/bottom gutter is 1px or 3px | It ranges **1–4px**; only left/top are fixed at 1px |
| Canvases capped at 2048×2048 | Cap is **asymmetric: ≤2048 wide, ~4096 tall** (`pix_prologue` = 1024×4080) |
| Format uniform per archive (`dxt5` = pix_common only) | Format is **per-texture**; archives can mix, and `dxt5` is common (~40%) |

## Worked example: `pix_error_ifs`

The simplest case — one canvas, one sprite:

```xml
<texture format="argb8888rev" name="tex000" ...>
  <size __type="2u16">722 62</size>          <!-- canvas = 722×62 px -->
  <image name="bar">
    <uvrect  __type="4u16">2 1442 2 122</uvrect>   <!-- /2 => x 1..721, y 1..61 (content) -->
    <imgrect __type="4u16">0 1444 0 124</imgrect>  <!-- /2 => x 0..722, y 0..62 (cell) -->
  </image>
</texture>
```

The `imgrect` fills the whole 722×62 canvas; the `uvrect` is inset 1px all around as the
bleed guard. The actual sampled sprite is 720×60.
