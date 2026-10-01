"""
1. Mean blur of all pictures in "Cropped and perspective corrected boards"
   -> saved in "Blurred Pictures"
2. Each blurred 500x500 picture is split into 5x5 tiles (100x100 px each).
   Every tile is filled with its mean BGR color and the values are written
   on the tile, with a yellow grid around the tiles
   -> saved in "Tile BGR Values"
Both output folders are emptied every time the program starts.
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
IMAGE_PATTERN = os.path.join(IMAGE_DIR, "*.jpg")

KERNEL_SIZE = (5, 5)   # mean blur window
TILE_SIZE = 100        # pixels per tile (width and height)
GRID = 5               # 5 x 5 tiles
BOARD_SIZE = TILE_SIZE * GRID  # 500


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
    Walk over the 5x5 grid, compute the mean BGR of each 100x100 tile,
    fill the ENTIRE tile with that mean color, draw the yellow grid, and
    write the values on the tile.
    Returns the mosaic image and a dict {(row, col): (B, G, R)}.
    """
    if img.shape[0] != BOARD_SIZE or img.shape[1] != BOARD_SIZE:
        print(f"[WARN] Image is {img.shape[1]}x{img.shape[0]}, "
              f"resizing to {BOARD_SIZE}x{BOARD_SIZE}")
        img = cv2.resize(img, (BOARD_SIZE, BOARD_SIZE))

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
# MAIN
# ----------------------------------------------------------------------

def main():
    prepare_folder(BLURRED_DIR)
    prepare_folder(TILE_DIR)

    files = sorted(glob.glob(IMAGE_PATTERN))
    if not files:
        print(f"[WARN] No .jpg images found in '{IMAGE_DIR}'")
        return

    # Step 1: blur
    for f in files:
        blurred = mean_blur_image(f)
        cv2.imwrite(os.path.join(BLURRED_DIR, os.path.basename(f)), blurred)
        print(f"[BLUR] {os.path.basename(f)}")

    # Step 2: read tile BGR values from the blurred pictures
    blurred_files = sorted(glob.glob(os.path.join(BLURRED_DIR, "*.jpg")))
    for f in blurred_files:
        img = cv2.imread(f)
        if img is None:
            print(f"[SKIP] Could not read {f}")
            continue

        vis, values = annotate_tiles(img)
        out_path = os.path.join(TILE_DIR, os.path.basename(f))
        cv2.imwrite(out_path, vis)

        print(f"\n{os.path.basename(f)}")
        for (row, col), (b, g, r) in values.items():
            print(f"  tile ({row},{col}): B={b:3d} G={g:3d} R={r:3d}")

    print(f"\nDone. Annotated images saved in '{TILE_DIR}'")


if __name__ == "__main__":
    main()