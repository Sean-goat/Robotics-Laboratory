"""
For every picture in "Cropped and perspective corrected boards":
1. A mean blur is applied to the image in memory (nothing is saved).
2. The blurred 500x500 image is split into 5x5 tiles (100x100 px each).
   The mean color of every tile is taken, converted to HSV, and shown as a
   mosaic with the mean HSV values written on each tile
   -> saved in "Tile HSV Values"
3. Each tile's mean HSV is classified (terrain types + crown tiles) with HSV
   thresholds. The closest type is written on the ORIGINAL (unblurred)
   picture. Exactly one tile per picture is always classified as a crown tile
   -> saved in "Classified Tiles"
Both output folders are emptied every time the program starts.

OpenCV HSV ranges: H = 0-179, S = 0-255, V = 0-255
"""

import cv2
import numpy as np
import glob
import os
import shutil

# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------

IMAGE_DIR = "Cropped and perspective corrected boards"
TILE_DIR = os.path.join(IMAGE_DIR, "Tile HSV Values")
CLASSIFIED_DIR = os.path.join(IMAGE_DIR, "Classified Tiles")
IMAGE_PATTERN = os.path.join(IMAGE_DIR, "*.jpg")

KERNEL_SIZE = (5, 5)   # mean blur window
TILE_SIZE = 100        # pixels per tile (width and height)
GRID = 5               # 5 x 5 tiles
BOARD_SIZE = TILE_SIZE * GRID  # 500

# name: ((H_min, S_min, V_min), (H_max, S_max, V_max))  -- raw values from the tables
TERRAIN_RANGES = {
    "Wheat":     ((25,  115, 131), (26,  245, 195)),
    "Forest":    ((32,  100, 49),  (46,  186, 75)),
    "Lake":      ((103, 162, 105), (105, 247, 159)),
    "Grassland": ((33,  146, 108), (44,  194, 158)),
    "Swamp":     ((21,  60,  85),  (23,  147, 135)),
    "Mine":      ((17,  118, 55),  (20,  166, 85)),
    "Table":     ((19,  92,  128), (22,  203, 172)),
}

CROWN_RANGES = {
    "Y Crown": ((29, 95, 70),  (33, 121, 146)),
    "R Crown": ((19, 60, 72),  (21, 145, 135)),
    "G Crown": ((31, 64, 48),  (40, 114, 112)),
    "B Crown": ((40, 21, 55),  (69, 33,  131)),
}

BASE_RANGES = {**TERRAIN_RANGES, **CROWN_RANGES}

# Tolerance added around each range, per channel (H, S, V)
BUFFER = (3, 15, 15)

# Position prior for the crown tile (row, col). Set to None to disable.
CROWN_POSITION = (2, 2)
CROWN_POSITION_BONUS = 100   # was 0.5, now the middle tile is always the crown tile

# How strongly the position counts. About 0.5 = strong hint, 100 = always forced.
CROWN_POSITION_BONUS = 0.5

def build_thresholds(buffer):
    """Widen every range by the buffer and clamp to the valid HSV range."""
    max_vals = (179, 255, 255)
    out = {}
    for name, (lo, hi) in BASE_RANGES.items():
        out[name] = (
            tuple(max(0, lo[i] - buffer[i]) for i in range(3)),
            tuple(min(max_vals[i], hi[i] + buffer[i]) for i in range(3)),
        )
    return out


THRESHOLDS = build_thresholds(BUFFER)


def is_crown(name):
    return name in CROWN_RANGES


# ----------------------------------------------------------------------
# FOLDER HANDLING
# ----------------------------------------------------------------------

def prepare_folder(folder):
    """Create the folder if missing, and delete everything inside it."""
    os.makedirs(folder, exist_ok=True)
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if os.path.isfile(path) or os.path.islink(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
    print(f"[INFO] Cleared folder: {folder}")


# ----------------------------------------------------------------------
# TILE HSV VALUES
# ----------------------------------------------------------------------

def fix_size(img):
    """Make sure the image is exactly 500x500."""
    if img.shape[0] != BOARD_SIZE or img.shape[1] != BOARD_SIZE:
        print(f"[WARN] Image is {img.shape[1]}x{img.shape[0]}, "
              f"resizing to {BOARD_SIZE}x{BOARD_SIZE}")
        img = cv2.resize(img, (BOARD_SIZE, BOARD_SIZE))
    return img


def get_tile_bgr(img, row, col):
    """Return the mean (B, G, R) of the 100x100 tile at (row, col)."""
    y1, x1 = row * TILE_SIZE, col * TILE_SIZE
    tile = img[y1:y1 + TILE_SIZE, x1:x1 + TILE_SIZE]
    b, g, r = tile.reshape(-1, 3).mean(axis=0)
    return int(round(b)), int(round(g)), int(round(r))


def bgr_to_hsv(bgr):
    """Convert one (B, G, R) color to OpenCV (H, S, V)."""
    pixel = np.uint8([[list(bgr)]])
    h, s, v = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0][0]
    return int(h), int(s), int(v)


def put_text_outlined(img, text, org, scale=0.4):
    """White text with a black outline, the same everywhere."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, text, org, font, scale, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, org, font, scale, (255, 255, 255), 1, cv2.LINE_AA)


def annotate_tiles(img):
    """
    Blur the image in memory, then compute the mean color of each 100x100
    tile, fill the tile with it, draw the yellow grid, and write the mean
    H, S, V on the tile.
    Returns the mosaic image and a dict {(row, col): (H, S, V)}.
    """
    img = cv2.blur(fix_size(img), KERNEL_SIZE)
    vis = np.zeros_like(img)
    values = {}

    for row in range(GRID):
        for col in range(GRID):
            bgr = get_tile_bgr(img, row, col)
            h, s, v = bgr_to_hsv(bgr)
            values[(row, col)] = (h, s, v)

            x1, y1 = col * TILE_SIZE, row * TILE_SIZE
            x2, y2 = x1 + TILE_SIZE, y1 + TILE_SIZE

            vis[y1:y2, x1:x2] = bgr
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 255), 1)

            put_text_outlined(vis, f"H:{h}", (x1 + 6, y1 + 35))
            put_text_outlined(vis, f"S:{s}", (x1 + 6, y1 + 55))
            put_text_outlined(vis, f"V:{v}", (x1 + 6, y1 + 75))

    return vis, values


# ----------------------------------------------------------------------
# CLASSIFICATION
# ----------------------------------------------------------------------

def score_against(hsv, name):
    lo, hi = THRESHOLDS[name]
    blo, bhi = BASE_RANGES[name]
    score = 0.0
    for i in range(3):
        center = (blo[i] + bhi[i]) / 2
        half = max((hi[i] - lo[i]) / 2, 1)
        score += ((hsv[i] - center) / half) ** 2
    
    final_score = score ** 0.5
    
    # Give Crown candidates a 25% boost in confidence:
    if is_crown(name):
        final_score *= 0.75  
        
    return final_score


def classify_tile(hsv, allowed=None):
    """
    Return (name, score) of the closest type. If 'allowed' is given, only
    those types are considered.
    """
    names = allowed if allowed is not None else list(THRESHOLDS)
    best_name, best_score = None, float("inf")
    for name in names:
        s = score_against(hsv, name)
        if s < best_score:
            best_name, best_score = name, s
    return best_name, best_score


def classify_all(values):
    """Classify all 25 tiles. Returns {(row, col): (name, score)}."""
    return {pos: classify_tile(hsv) for pos, hsv in values.items()}


def enforce_single_crown(results, values, image_name):
    """
    Guarantee exactly one crown tile per picture.

    Every tile gets a 'crown-likeness' margin: the score of its best crown
    type minus the score of its best terrain type. The lower the margin, the
    more the tile looks like a crown tile.
    - 0 crown tiles: the tile with the lowest margin becomes the crown tile.
    - 2 or more: only the tile with the lowest margin stays a crown tile,
      the others go back to their closest terrain type.
    """
    terrain = list(TERRAIN_RANGES)
    crowns = list(CROWN_RANGES)

    best_terrain = {pos: classify_tile(hsv, allowed=terrain) for pos, hsv in values.items()}
    best_crown = {pos: classify_tile(hsv, allowed=crowns) for pos, hsv in values.items()}
    margin = {pos: best_crown[pos][1] - best_terrain[pos][1] for pos in values}

    if CROWN_POSITION is not None:
        margin[CROWN_POSITION] -= CROWN_POSITION_BONUS

    winner = min(margin, key=margin.get)

    current = [pos for pos, (name, _) in results.items() if is_crown(name)]
    if current != [winner]:
        print(f"[CHECK] {image_name}: found {len(current)} crown tiles, "
              f"forced to one at tile {winner}")

    for pos in values:
        results[pos] = best_crown[pos] if pos == winner else best_terrain[pos]

    return results


def put_label_centered(img, text, x1, y1):
    """Write text centered on the tile whose top-left corner is (x1, y1)."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.45
    (w, h), _ = cv2.getTextSize(text, font, scale, 1)
    org = (x1 + (TILE_SIZE - w) // 2, y1 + (TILE_SIZE + h) // 2)
    put_text_outlined(img, text, org, scale)


def draw_classification(original, results):
    """Write the tile names on a copy of the original picture."""
    vis = fix_size(original).copy()
    for (row, col), (name, _) in results.items():
        put_label_centered(vis, name, col * TILE_SIZE, row * TILE_SIZE)
    return vis


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

def main():
    prepare_folder(TILE_DIR)
    prepare_folder(CLASSIFIED_DIR)

    files = sorted(glob.glob(IMAGE_PATTERN))
    if not files:
        print(f"[WARN] No .jpg images found in '{IMAGE_DIR}'")
        return

    for f in files:
        name = os.path.basename(f)
        original = cv2.imread(f)
        if original is None:
            print(f"[SKIP] Could not read {name}")
            continue

        # Blur in memory -> tile means -> HSV values
        mosaic, values = annotate_tiles(original)
        cv2.imwrite(os.path.join(TILE_DIR, name), mosaic)

        # Classify, then write labels on the original picture
        results = classify_all(values)
        results = enforce_single_crown(results, values, name)

        classified = draw_classification(original, results)
        cv2.imwrite(os.path.join(CLASSIFIED_DIR, name), classified)

        print(f"\n{name}")
        for (row, col), (h, s, v) in values.items():
            label, score = results[(row, col)]
            print(f"  tile ({row},{col}): H={h:3d} S={s:3d} V={v:3d}  "
                  f"-> {label} (score {score:.2f})")

    print(f"\nDone. Classified images saved in '{CLASSIFIED_DIR}'")


if __name__ == "__main__":
    main()