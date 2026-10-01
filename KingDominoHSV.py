"""
1. Mean blur of all pictures in "Cropped and perspective corrected boards"
   -> saved in "Blurred Pictures"
2. Each blurred 500x500 picture is split into 5x5 tiles (100x100 px each).
   Every tile is filled with its mean color, with the mean HSV values on it
   -> saved in "Tile HSV Values"
3. Each tile's mean HSV is classified with HSV min/max thresholds. The tile
   name is written on the ORIGINAL (unblurred) picture. Unsure tiles get no text
   -> saved in "Classified Tiles"
All output folders are emptied every time the program starts.

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
BLURRED_DIR = os.path.join(IMAGE_DIR, "Blurred Pictures")
TILE_DIR = os.path.join(IMAGE_DIR, "Tile HSV Values")
CLASSIFIED_DIR = os.path.join(IMAGE_DIR, "Classified Tiles")
IMAGE_PATTERN = os.path.join(IMAGE_DIR, "*.jpg")

KERNEL_SIZE = (5, 5)   # mean blur window
TILE_SIZE = 100        # pixels per tile (width and height)
GRID = 5               # 5 x 5 tiles
BOARD_SIZE = TILE_SIZE * GRID  # 500

# name: ((H_min, S_min, V_min), (H_max, S_max, V_max))  -- raw values from the table
BASE_RANGES = {
    "Wheat":     ((25,  228, 169), (26,  245, 195)),
    "Forest":    ((32,  116, 49),  (46,  186, 64)),
    "Lake":      ((103, 162, 105), (105, 247, 159)),
    "Grassland": ((33,  146, 108), (44,  194, 158)),
    "Swamp":     ((21,  60,  85), (23,  147, 135)),
    "Mine":      ((17,  118, 55),  (20,  166, 85)),
    "Table":     ((19,  92,  128), (22,  203, 172)),
}

# Tolerance added around each range, per channel (H, S, V)
BUFFER = (3, 15, 15)


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
    Compute the mean color of each 100x100 tile, fill the tile with it,
    draw the yellow grid, and write the mean H, S, V on the tile.
    Returns the mosaic image and a dict {(row, col): (H, S, V)}.
    """
    img = fix_size(img)
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

def classify_tile(hsv):
    """
    Return the tile type whose HSV range is closest to the mean HSV.

    For each type, the distance in every channel (H, S, V) is measured from the
    center of its range and divided by the half-width of the buffered range,
    so H, S and V count equally. The type with the smallest combined distance
    wins. A tile inside a range scores low, a tile far outside scores high,
    but the closest type is always returned.
    """
    best_name = None
    best_score = float("inf")

    for name, (lo, hi) in THRESHOLDS.items():
        blo, bhi = BASE_RANGES[name]
        score = 0.0
        for i in range(3):
            center = (blo[i] + bhi[i]) / 2
            half = max((hi[i] - lo[i]) / 2, 1)
            score += ((hsv[i] - center) / half) ** 2
        score = score ** 0.5

        if score < best_score:
            best_score = score
            best_name = name

    return best_name


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
    for (row, col), hsv in values.items():
        name = classify_tile(hsv)
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

    # Step 2 + 3: HSV mosaic from blurred pictures, labels on originals
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
        for (row, col), (h, s, v) in values.items():
            label = labels[(row, col)] or "unsure"
            print(f"  tile ({row},{col}): H={h:3d} S={s:3d} V={v:3d}  -> {label}")

    print(f"\nDone. Classified images saved in '{CLASSIFIED_DIR}'")


if __name__ == "__main__":
    main()