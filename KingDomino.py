"""
1. Mean blur of all pictures in "Cropped and perspective corrected boards"
   -> saved in "Blurred Pictures"
2. Each blurred 500x500 picture is split into 5x5 tiles (100x100 px each).
   Every tile is filled with its mean BGR color, with the values written on it
   -> saved in "Tile BGR Values"
3. Each tile's mean BGR is classified with BGR min/max thresholds. The tile
   name is written on the ORIGINAL (unblurred) picture. Unsure tiles get no text
   -> saved in "Classified Tiles"
All output folders are emptied every time the program starts.
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
BLURRED_DIR = os.path.join(IMAGE_DIR, "Blurred Pictures")
TILE_DIR = os.path.join(IMAGE_DIR, "Tile BGR Values")
CLASSIFIED_DIR = os.path.join(IMAGE_DIR, "Classified Tiles")
IMAGE_PATTERN = os.path.join(IMAGE_DIR, "*.jpg")

KERNEL_SIZE = (40, 40)   # mean blur window
TILE_SIZE = 100        # pixels per tile (width and height)
GRID = 5               # 5 x 5 tiles
BOARD_SIZE = TILE_SIZE * GRID  # 500

# Extra tolerance added around every min/max range (0 = exactly your table).
# Increase it (e.g. 5 or 10) if too many tiles end up "unsure".
MARGIN = 0

# name: ((B_min, G_min, R_min), (B_max, G_max, R_max))  -- raw values from the table
BASE_RANGES = {
    "Wheat":     ((5,   146, 170), (18,  168, 188)),
    "Forest":    ((13,  53,  40),  (39,  67,  56)),
    "Lake":      ((101, 75,  5),   (162, 88,  50)),
    "Grassland": ((20,  112, 97),  (36,  151, 113)),
    "Swamp":     ((42,  96,  110), (95,  128, 133)),
    "Mine":      ((32,  62,  70),  (33,  62,  75)),
    "Table":     ((26,  94,  128), (110, 152, 176)),
}

BUFFER = 12  # tolerance added around every range


def build_thresholds(buffer):
    """Widen every range by the buffer and clamp to the valid 0-255 range."""
    out = {}
    for name, (lo, hi) in BASE_RANGES.items():
        out[name] = (
            tuple(max(0, v - buffer) for v in lo),
            tuple(min(255, v + buffer) for v in hi),
        )
    return out


THRESHOLDS = build_thresholds(BUFFER)


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
# BLURRING
# ----------------------------------------------------------------------

def mean_blur_image(image_path, kernel_size=KERNEL_SIZE):
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    return cv2.blur(img, kernel_size)


# ----------------------------------------------------------------------
# TILE BGR VALUES
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


def put_text_outlined(img, text, org, scale=0.4):
    """White text with a black outline, the same on every tile."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, text, org, font, scale, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, org, font, scale, (255, 255, 255), 1, cv2.LINE_AA)


def annotate_tiles(img):
    """
    Compute the mean BGR of each 100x100 tile, fill the tile with it,
    draw the yellow grid, and write the values on the tile.
    Returns the mosaic image and a dict {(row, col): (B, G, R)}.
    """
    img = fix_size(img)
    vis = np.zeros_like(img)
    values = {}

    for row in range(GRID):
        for col in range(GRID):
            b, g, r = get_tile_bgr(img, row, col)
            values[(row, col)] = (b, g, r)

            x1, y1 = col * TILE_SIZE, row * TILE_SIZE
            x2, y2 = x1 + TILE_SIZE, y1 + TILE_SIZE

            vis[y1:y2, x1:x2] = (b, g, r)
            cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 255), 1)

            put_text_outlined(vis, f"B:{b}", (x1 + 6, y1 + 35))
            put_text_outlined(vis, f"G:{g}", (x1 + 6, y1 + 55))
            put_text_outlined(vis, f"R:{r}", (x1 + 6, y1 + 75))

    return vis, values


# ----------------------------------------------------------------------
# CLASSIFICATION
# ----------------------------------------------------------------------

def classify_tile(bgr):
    """
    Return the tile name whose buffered range contains the mean BGR.
    If several ranges match, pick the one whose original range center
    is closest. Return None (unsure) if nothing matches.
    """
    matches = []
    for name, (lo, hi) in THRESHOLDS.items():
        if all(lo[i] <= bgr[i] <= hi[i] for i in range(3)):
            base_lo, base_hi = BASE_RANGES[name]
            center = [(base_lo[i] + base_hi[i]) / 2 for i in range(3)]
            dist = sum((bgr[i] - center[i]) ** 2 for i in range(3)) ** 0.5
            matches.append((dist, name))

    if not matches:
        return None
    return min(matches)[1]


def put_label_centered(img, text, x1, y1):
    """Write text centered on the tile whose top-left corner is (x1, y1)."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.45
    (w, h), _ = cv2.getTextSize(text, font, scale, 1)
    org = (x1 + (TILE_SIZE - w) // 2, y1 + (TILE_SIZE + h) // 2)
    put_text_outlined(img, text, org, scale)


def draw_classification(original, values):
    """Write the tile names on a copy of the original picture."""
    vis = fix_size(original).copy()
    labels = {}
    for (row, col), bgr in values.items():
        name = classify_tile(bgr)
        labels[(row, col)] = name
        if name is not None:
            put_label_centered(vis, name, col * TILE_SIZE, row * TILE_SIZE)
    return vis, labels


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

def main():
    prepare_folder(BLURRED_DIR)
    prepare_folder(TILE_DIR)
    prepare_folder(CLASSIFIED_DIR)

    files = sorted(glob.glob(IMAGE_PATTERN))
    if not files:
        print(f"[WARN] No .jpg images found in '{IMAGE_DIR}'")
        return

    # Step 1: blur
    for f in files:
        blurred = mean_blur_image(f)
        cv2.imwrite(os.path.join(BLURRED_DIR, os.path.basename(f)), blurred)
        print(f"[BLUR] {os.path.basename(f)}")

    # Step 2 + 3: tile values from blurred pictures, labels on originals
    for f in files:
        name = os.path.basename(f)
        blurred = cv2.imread(os.path.join(BLURRED_DIR, name))
        original = cv2.imread(f)
        if blurred is None or original is None:
            print(f"[SKIP] Could not read {name}")
            continue

        mosaic, values = annotate_tiles(blurred)
        cv2.imwrite(os.path.join(TILE_DIR, name), mosaic)

        classified, labels = draw_classification(original, values)
        cv2.imwrite(os.path.join(CLASSIFIED_DIR, name), classified)

        print(f"\n{name}")
        for (row, col), (b, g, r) in values.items():
            label = labels[(row, col)] or "unsure"
            print(f"  tile ({row},{col}): B={b:3d} G={g:3d} R={r:3d}  -> {label}")

    print(f"\nDone. Classified images saved in '{CLASSIFIED_DIR}'")


if __name__ == "__main__":
    main()