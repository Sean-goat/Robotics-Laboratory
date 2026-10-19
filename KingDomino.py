"""
1. Mean blur of all pictures in "Cropped and perspective corrected boards"
   -> saved in "Blurred Pictures"
2. Each blurred 500x500 picture is split into 5x5 tiles (100x100 px each).
   Every tile is filled with its mean color, with the mean HSV values on it
   -> saved in "Tile HSV Values"
3. Each tile's mean HSV is classified (terrain types + crown tiles) with HSV
   min/max thresholds. The closest type is written on the ORIGINAL (unblurred)
   picture. Exactly one tile per picture is always classified as a crown tile
   -> saved in "Classified Tiles"
4. Neighbouring tiles (up/down/left/right) of the same type are grouped with
   the grassfire method. An outline is drawn around every group on the
   ORIGINAL picture, with the number of tiles in the group
   -> saved in "Grouped Tiles"
All output folders are emptied every time the program starts.

OpenCV HSV ranges: H = 0-179, S = 0-255, V = 0-255
"""

import cv2                          # Image processing library
import numpy as np                  # Holds image data as arrays, which is good for working with the pixels
import glob                         # Finds files like .JPG
import os                           # Handles file paths and folders
import shutil                       # Higher level file operations, for deleating whole folders
from collections import deque       # A queue like list used for the grassfire grouping

# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------

# Sets up all of the directions for where to look for pictues and where to leave them agian
IMAGE_DIR = "Cropped and perspective corrected boards"
ORIGINAL_DIR = os.path.join(IMAGE_DIR, "Original Pictures")
BLURRED_DIR = os.path.join(IMAGE_DIR, "Blurred Pictures")
TILE_DIR = os.path.join(IMAGE_DIR, "Tile HSV Values")
CLASSIFIED_DIR = os.path.join(IMAGE_DIR, "Classified Tiles")
GROUPED_DIR = os.path.join(IMAGE_DIR, "Grouped Tiles")
IMAGE_PATTERN = os.path.join(ORIGINAL_DIR, "*.jpg")

KERNEL_SIZE = (5, 5)   # mean blur window
TILE_SIZE = 100        # pixels per tile (width and height)
GRID = 5               # 5 x 5 tiles
BOARD_SIZE = TILE_SIZE * GRID  # 500

# all of the HSV thresholds using HSV. A minimum HSV and Maximum HSV have been set
# for the tiles
THRESHOLDS = {
    "Wheat":     ((22, 100, 116), (29, 255, 210)),
    "Forest":    ((29, 101, 34),  (49, 201, 79)),
    "Lake":      ((100, 147, 90), (108, 255, 174)),
    "Grassland": ((30, 131, 93),  (47, 209, 173)),
    "Swamp":     ((18, 45, 70),   (26, 162, 150)),
    "Mine":      ((14, 103, 40),  (23, 181, 100)),
    "Table":     ((16, 77, 113),  (25, 218, 187)),
    "Y Crown":   ((26, 80, 55),   (36, 136, 161)),
    "R Crown":   ((13, 39, 42),   (27, 157, 143)),
    "G Crown":   ((28, 49, 33),   (43, 129, 127)),
    "B Crown":   ((37, 6, 40),    (72, 48, 146)),
}

# two lists of tile names
TERRAIN_NAMES = ["Wheat", "Forest", "Lake", "Grassland", "Swamp", "Mine", "Table"]
CROWN_NAMES = ["Y Crown", "R Crown", "G Crown", "B Crown"]

# outline color (B, G, R) per type in the grouped pictures to make it look snazzy 💅
GROUP_COLORS = {
    "Wheat":     (0, 255, 255),
    "Forest":    (0, 180, 0),
    "Lake":      (255, 128, 0),
    "Grassland": (0, 255, 128),
    "Swamp":     (180, 105, 255),
    "Mine":      (0, 128, 255),
    "Table":     (200, 200, 200),
}
CROWN_COLOR = (255, 0, 255)

# Neighbours that count as connected: up, down, left, right. Because of (row,col)
NEIGHBORS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
TINT_ALPHA = 0.20     # Alpha value for the tint/transparency
OUTLINE_INSET = 3     # How far the outline is from the edge of the tile
BADGE_RADIUS = 18     # Size of the tile count circle

# to check if a tile is a crown tile, because we have more than one type of crown tile, returns true or false
def is_crown(name): 
    return name in CROWN_NAMES


# ----------------------------------------------------------------------
# FOLDER HANDLING
# ----------------------------------------------------------------------


def prepare_folder(folder):
    """Create the folder if missing, and delete everything inside it for good 😈"""
    os.makedirs(folder, exist_ok=True)                      # Creates the folder, if the folder already exists, then there is no error
    for name in os.listdir(folder):                         # Gets the names of everything (items) inside the folder and uses a for loop to loop over them
        path = os.path.join(folder, name)                   # Gets the full path to the current item so it knows exatly what to delete
        if os.path.isfile(path) or os.path.islink(path):    # Checks if the item is a normal file or a shortcut
            os.remove(path)                                 # Deletes that file or link ;)
        elif os.path.isdir(path):                           # if else it checks whether the item is a subfolder
            shutil.rmtree(path)                             # Deletes the subfolder and everything inside it
    print(f"[INFO] Cleared folder: {folder}")               # Prints a message to see which folder was cleared   


# ----------------------------------------------------------------------
# BLURRING
# ----------------------------------------------------------------------

def mean_blur_image(image_path, kernel_size):                               # Takes an image path and a kernal size to blur a picture
    img = cv2.imread(image_path)                                            # Reads the picture in an array of pixels in B, G, R order
    if img is None:                                                         # Checks whether the loading failed
        raise FileNotFoundError(f"Could not read image: {image_path}")      # Stops the program with an error message
    return cv2.blur(img, kernel_size)                                       # Returns the blured picture with openCV, from a given kernel size


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

def score_against(hsv, name):
    """
    Distance from the mean HSV to the center of one type's range.
    Every channel is divided by the half-width of the range, so
    H, S and V count equally. Lower = closer.
    """
    lo, hi = THRESHOLDS[name]
    score = 0.0
    for i in range(3):
        center = (lo[i] + hi[i]) / 2
        half = max((hi[i] - lo[i]) / 2, 1)
        score += ((hsv[i] - center) / half) ** 2
    return score ** 0.5


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
    terrain = TERRAIN_NAMES
    crowns = CROWN_NAMES

    best_terrain = {pos: classify_tile(hsv, allowed=terrain) for pos, hsv in values.items()}
    best_crown = {pos: classify_tile(hsv, allowed=crowns) for pos, hsv in values.items()}
    margin = {pos: best_crown[pos][1] - best_terrain[pos][1] for pos in values}

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
# GRASSFIRE GROUPING
# ----------------------------------------------------------------------

def ignite_fire(types, ids, start, group_id):
    """
    Burn the group that the start tile belongs to.
    Every connected tile (up/down/left/right) of the SAME type gets
    group_id in 'ids'. Returns the list of tiles that were burned.
    """
    start_type = types[start]
    burn_queue = deque()
    members = []

    # Only ignite if the start tile has not been burned yet
    if ids[start] == 0:
        burn_queue.append(start)

    while len(burn_queue) > 0:
        current_pos = burn_queue.pop()
        if ids[current_pos] != 0:
            continue

        # Burn current_pos with the current id
        ids[current_pos] = group_id
        members.append(current_pos)

        # Add connections to burn_queue
        r, c = current_pos
        for dr, dc in NEIGHBORS:
            nxt = (r + dr, c + dc)
            if nxt in types and ids[nxt] == 0 and types[nxt] == start_type:
                burn_queue.append(nxt)

    return members


def find_groups(results):
    """
    Loop over all tiles and ignite a fire on every tile that has not been
    burned yet. Returns {group_id: (type_name, [tiles])}.
    """
    types = {pos: name for pos, (name, _) in results.items()}
    ids = {pos: 0 for pos in types}   # 0 = not burned
    groups = {}
    next_id = 1

    for row in range(GRID):
        for col in range(GRID):
            pos = (row, col)
            if ids[pos] == 0:
                members = ignite_fire(types, ids, pos, next_id)
                groups[next_id] = (types[pos], members)
                next_id += 1

    return groups


def put_text_centered(img, text, cx, cy, scale, color=(0, 0, 0), thickness=2):
    """Plain text centered on pixel (cx, cy)."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    (w, h), _ = cv2.getTextSize(text, font, scale, thickness)
    org = (int(cx - w / 2), int(cy + h / 2))
    cv2.putText(img, text, org, font, scale, color, thickness, cv2.LINE_AA)


def draw_groups(original, groups):
    """
    Light color tint per group, a thin outline inside the group, and a small
    circle badge with the number of tiles.
    """
    base = fix_size(original)

    # Pass 1: tint every group in its type color
    tint = base.copy()
    prepared = []
    for group_id, (name, members) in groups.items():
        mask = np.zeros((BOARD_SIZE, BOARD_SIZE), np.uint8)
        for (r, c) in members:
            mask[r * TILE_SIZE:(r + 1) * TILE_SIZE,
                 c * TILE_SIZE:(c + 1) * TILE_SIZE] = 255
        color = CROWN_COLOR if is_crown(name) else GROUP_COLORS.get(name, (255, 255, 255))
        tint[mask > 0] = color
        prepared.append((members, mask, color))

    vis = cv2.addWeighted(tint, TINT_ALPHA, base, 1 - TINT_ALPHA, 0)

    # Pass 2: outlines and badges on top
    kernel = np.ones((2 * OUTLINE_INSET + 1, 2 * OUTLINE_INSET + 1), np.uint8)
    for members, mask, color in prepared:
        inset = cv2.erode(mask, kernel)
        contours, _ = cv2.findContours(inset, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, contours, -1, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.drawContours(vis, contours, -1, color, 2, cv2.LINE_AA)

        # Badge on the tile of the group closest to the group's center
        cr = sum(r for r, _ in members) / len(members)
        cc = sum(c for _, c in members) / len(members)
        r, c = min(members, key=lambda m: (m[0] - cr) ** 2 + (m[1] - cc) ** 2)
        cx = c * TILE_SIZE + TILE_SIZE // 2
        cy = r * TILE_SIZE + TILE_SIZE // 2

        cv2.circle(vis, (cx, cy), BADGE_RADIUS, color, -1, cv2.LINE_AA)
        cv2.circle(vis, (cx, cy), BADGE_RADIUS, (0, 0, 0), 2, cv2.LINE_AA)
        put_text_centered(vis, str(len(members)), cx, cy, 0.6)

    return vis


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

def main():
    prepare_folder(BLURRED_DIR)
    prepare_folder(TILE_DIR)
    prepare_folder(CLASSIFIED_DIR)
    prepare_folder(GROUPED_DIR)

    files = sorted(glob.glob(IMAGE_PATTERN))
    if not files:
        print(f"[WARN] No .jpg images found in '{ORIGINAL_DIR}'")
        return

    # Step 1: blur
    for f in files:
        blurred = mean_blur_image(f, KERNEL_SIZE)
        cv2.imwrite(os.path.join(BLURRED_DIR, os.path.basename(f)), blurred)
        print(f"[BLUR] {os.path.basename(f)}")

    # Step 2 + 3 + 4
    for f in files:
        name = os.path.basename(f)
        blurred = cv2.imread(os.path.join(BLURRED_DIR, name))
        original = cv2.imread(f)
        if blurred is None or original is None:
            print(f"[SKIP] Could not read {name}")
            continue

        mosaic, values = annotate_tiles(blurred)
        cv2.imwrite(os.path.join(TILE_DIR, name), mosaic)

        results = classify_all(values)
        results = enforce_single_crown(results, values, name)

        classified = draw_classification(original, results)
        cv2.imwrite(os.path.join(CLASSIFIED_DIR, name), classified)

        groups = find_groups(results)
        grouped = draw_groups(original, groups)
        cv2.imwrite(os.path.join(GROUPED_DIR, name), grouped)

        print(f"\n{name}")
        for (row, col), (h, s, v) in values.items():
            label, score = results[(row, col)]
            print(f"  tile ({row},{col}): H={h:3d} S={s:3d} V={v:3d}  "
                  f"-> {label} (score {score:.2f})")
        print(f"  Groups ({len(groups)}):")
        for gid, (gname, members) in groups.items():
            print(f"    #{gid} {gname}: {len(members)} tile(s)")

    print(f"\nDone. Grouped images saved in '{GROUPED_DIR}'")


if __name__ == "__main__":
    main()