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

def get_tile_bgr(img, row, col):
    """Return the mean (B, G, R) of the 100x100 tile at (row, col)."""
    y1, x1 = row * TILE_SIZE, col * TILE_SIZE               # Finds the top left pixel of a tile
    tile = img[y1:y1 + TILE_SIZE, x1:x1 + TILE_SIZE]        # separats the image in to a 3d NumPy array, with 100 rows, 100 columns, and 3 color values per pixel
    b, g, r = tile.reshape(-1, 3).mean(axis=0)              # Turns the 3D array into a 2D list of 10,000 pixels (B, G, R), then averages each color channel over all pixels
    return int(round(b)), int(round(g)), int(round(r))      # Rounds each value to the nearest whole number and converts it to a Python integer


def bgr_to_hsv(bgr):
    """Convert one (B, G, R) color to OpenCV (H, S, V)."""
    pixel = np.uint8([[list(bgr)]])                             # Wraps the color in a 1x1 "image" (shape 1, 1, 3) of unsigned 8 bit integers, because cvtColor only accepts images
    h, s, v = cv2.cvtColor(pixel, cv2.COLOR_BGR2HSV)[0][0]      # Converts the 1x1 image to HSV, [0][0] picks out the single pixel (row and column), and h, s, v receive its three values
    return int(h), int(s), int(v)                               # Turns the NumPy numbers into normal Python integers


def annotate_tiles(img):
    """
    Compute the mean color of each 100x100 tile, fill the tile with it,
    draw the yellow grid, and write the mean H, S, V on the tile.
    Returns the mosaic image and a dict {(row, col): (H, S, V)}.
    """
    vis = np.zeros_like(img)            # Makes a black picture with the same size and type as the input
    values = {}                         # An empty dictionary that will later hold the 25 HSV values
    font = cv2.FONT_HERSHEY_SIMPLEX     # Sets the font
    
    for row in range(GRID):                         # Go through all 5 × 5 = 25 tiles
        for col in range(GRID):                     # Go through all 5 × 5 = 25 tiles
            bgr = get_tile_bgr(img, row, col)       # Gives the tile's average color as (B, G, R)
            h, s, v = bgr_to_hsv(bgr)               # Uses the function to convert to HSV
            values[(row, col)] = (h, s, v)          # saves the HSV under the sile position

            # To find the tile location in the 500 x 500 image
            x1, y1 = col * TILE_SIZE, row * TILE_SIZE 
            x2, y2 = x1 + TILE_SIZE, y1 + TILE_SIZE

            # Colors the whole tile area in its mean color
            vis[y1:y2, x1:x2] = bgr 

            # Maybe this put the H, S, V values on the image, not sure though 🤔
            cv2.putText(vis, f"H:{h}", (x1 + 6, y1 + 35), font, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(vis, f"S:{s}", (x1 + 6, y1 + 55), font, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(vis, f"V:{v}", (x1 + 6, y1 + 75), font, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

    return vis, values # Returns the picture and the dictionary


# ----------------------------------------------------------------------
# CLASSIFICATION
# ----------------------------------------------------------------------

def score_against(hsv, name):
    """
    Distance from the mean HSV to the center of one type's range.
    Every channel is divided by the half-width of the range, so
    H, S and V count equally. Lower = closer.

    This is the related idea to kNN
    """
    lo, hi = THRESHOLDS[name]                           # Looks up the minimum and maximum HSV for a tile type
    score = 0.0                                         # Makes the variabel for the calculations
    for i in range(3):                                  # A loop to loop through all 3 HSV channels
        center = (lo[i] + hi[i]) / 2                    # Finds the avrage of the HSV for a type threshold
        half = max((hi[i] - lo[i]) / 2, 1)              # It finds half the width. max then picks the larger of that and 1, so it never becomes 0
        score += ((hsv[i] - center) / half) ** 2        # Tells how far a H, S or V value is from the middle of the range. Then this distance is squred and all of the channels are added up
    return score ** 0.5                                 # Takes the square root of the sum and returns that


def classify_tile(hsv, allowed=None):
    """
    Return (name, score) of the closest type. If 'allowed' is given, only
    those types are considered.

    This is a very simplified version of Gaussian naive Bayes 
    with lowest number getting classifyed.
    No probability is used here.
    """
    names = allowed if allowed is not None else list(THRESHOLDS)        # Types to check: only the given list, or all types if none is given
    best_name, best_score = None, float("inf")                          # Sets the starting "best so far"
    for name in names:                                                  # Loops over the sent types
        s = score_against(hsv, name)                                    # Calculates the distance from the tile to that type
        if s < best_score:                                              # Checks whether this type is closer than the best one so far
            best_name, best_score = name, s                             # If so then replace the best with this one
    return best_name, best_score                                        # Returns the closest type and its score


def classify_all(values):                                                   # The first time classify_tile get called here all of the tiles gets classified. They can be any type including crown types
    """Classify all 25 tiles. Returns {(row, col): (name, score)}."""
    return {pos: classify_tile(hsv) for pos, hsv in values.items()}         # Returns a dictionary with (name, score) pairs, as well as the location on the board

# enforce_single_crown have been made by AI
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

    # Two lists of allowed names, the ones getting passed to classify_all
    terrain = TERRAIN_NAMES
    crowns = CROWN_NAMES

    best_terrain = {pos: classify_tile(hsv, allowed=terrain) for pos, hsv in values.items()}        # Closest terrain type and its score for every tile
    best_crown = {pos: classify_tile(hsv, allowed=crowns) for pos, hsv in values.items()}           # Same for the closest crown type
    margin = {pos: best_crown[pos][1] - best_terrain[pos][1] for pos in values}                     # Best crown score minus best terrain score for every tile. A low margin means the tile looks like a crown

    winner = min(margin, key=margin.get)        # Finds the position with the lowest margin. min goes over the dictionary's keys and key=margin.get compares them by their margin values

    # The winner gets its best crown type, every other tile its best terrain type. This replaces the first pass, so there is always exactly one crown
    for pos in values:                                                          
        results[pos] = best_crown[pos] if pos == winner else best_terrain[pos]

    return results      # Returns the dictionary with the label and score of all 25 tiles


def put_label_centered(img, text, x1, y1):
    """Write text centered on the tile whose top-left corner is (x1, y1)."""

    font = cv2.FONT_HERSHEY_SIMPLEX         # Set the font
    scale = 0.5                            # Set the text scale

    (w, h), _ = cv2.getTextSize(text, font, scale, 1)                               # Measures the text before drawing it. It returns the width w and height h in pixels. The _ ignores that baseline, and the 1 is the thickness.
    org = (x1 + (TILE_SIZE - w) // 2, y1 + (TILE_SIZE + h) // 2)                    # This is the point where the text starts. Horizontaly and verticaly
    cv2.putText(img, text, org, font, scale, (255, 255, 255), 1, cv2.LINE_AA)       # Draws the text at org in white (255, 255, 255), with thickness 1 and smooth edges (cv2.LINE_AA)


def draw_classification(original, results):
    """Write the tile names on a copy of the original picture."""
    vis = original.copy()                                                       # Makes a separate copy of the picture
    for (row, col), (name, _) in results.items():                               # loops over the results dictionary. The result looks like (row, col), (name, _)
        put_label_centered(vis, name, col * TILE_SIZE, row * TILE_SIZE)         # Writes the name in the middle of the tile. Note the order x1 comes from the column and y1 from the row
    return vis                                                                  # Retuns the finished picture with tile names


# ----------------------------------------------------------------------
# GRASSFIRE GROUPING
# ----------------------------------------------------------------------

def ignite_fire(types, ids, start, group_id):       # types: dictionary with the type name of each tile position. ids: dictionary with the group number per tile (0 = not burned yet). start: position where the fire starts. group_id: the number of this group
    """
    Burn the group that the start tile belongs to.
    Every connected tile (up/down/left/right) of the SAME type gets
    group_id in 'ids'. Returns the list of tiles that were burned.
    """
    start_type = types[start]       # saves the type of the tile type, so only the same type gets burned
    burn_queue = deque()            # The list of tiles waiting to be burned
    members = []                    # Saves tiles that have been burned

    # Only ignite if the start tile has not been burned yet
    if ids[start] == 0:                 # If a tile have 0 id
        burn_queue.append(start)        # Then the fire needs to start there

    while len(burn_queue) > 0:              # Loops until there are no more tiles waiting in queue
        current_pos = burn_queue.pop()      # Takes a tile from the queue
        if ids[current_pos] != 0:           # skips the tile if it was burned previus
            continue                        # skips like a stone

        # Burn current_pos with the current id
        ids[current_pos] = group_id         # Burns a tile. Giving it an id
        members.append(current_pos)         # Adds it to the group list

        # Add connections to burn_queue
        r, c = current_pos                                                          # This splits it into rows and columns
        for dr, dc in NEIGHBORS:                                                    # Loops over all of the directions in where to look for neighbors
            nxt = (r + dr, c + dc)                                                  # This adds the step to the current position, so the neighbors
            if nxt in types and ids[nxt] == 0 and types[nxt] == start_type:         # First it checks if it is a position on the board. Then it checks if it have been burned. Then it checks if it have been burned 
                burn_queue.append(nxt)                                              # The neighbour gets sent to the queue

    return members      # Returns the list of its tiles, that is in the menbers that have been burned


def find_groups(results):
    """
    Loop over all tiles and ignite a fire on every tile that has not been
    burned yet. Returns {group_id: (type_name, [tiles])}.
    """
    types = {pos: name for pos, (name, _) in results.items()}       # Makes the types dictionary that ignite_fire needs, results has (name, score) pairs
    ids = {pos: 0 for pos in types}                                 # Gives every tile the group number 0
    groups = {}                                                     # Will hold the finished groups
    next_id = 1                                                     # The number for the next group

    for row in range(GRID):                                             # goes through all 25 tiles
        for col in range(GRID):                                         # goes through all 25 tiles
            pos = (row, col)                                            # gets the position
            if ids[pos] == 0:                                           # checks if the tile is unburned
                members = ignite_fire(types, ids, pos, next_id)         # Burns the group around this tile
                groups[next_id] = (types[pos], members)                 # Saves the group under its number, with its type name and its tiles
                next_id += 1                                            # Increment the counter

    return groups       # Returns a dictionary with grupe type and locations


def put_text_centered(img, text, cx, cy, scale, color=(0, 0, 0), thickness=2):      # It gets img: picture to write on. text: is a string. cx and cy is the center pixel where the text is written. scale is the font size. color: is set to black. thickness: is the line thickness
    """Plain text centered on pixel (cx, cy)."""
    font = cv2.FONT_HERSHEY_SIMPLEX                                                 # The font, I think maybe
    (w, h), _ = cv2.getTextSize(text, font, scale, thickness)                       # Measures the width w and height h of the text
    org = (int(cx - w / 2), int(cy + h / 2))                                        # Is the start point of the text
    cv2.putText(img, text, org, font, scale, color, thickness, cv2.LINE_AA)         # Draws the text at org

# draw_groups have been made by AI
def draw_groups(original, groups):
    """
    Light color tint per group, a thin outline inside the group, and a small
    circle badge with the number of tiles.
    """
    
    base = original         # This is the picture everything is drawn on

    # Pass 1: tint every group in its type color
    tint = base.copy()      # This makes a separate copy of the original picture
    prepared = []           # This is an empty list. During the loop, each group adds one tuple to it
    
    for group_id, (name, members) in groups.items():                #  It loops over each group: its number, type name and tiles
        mask = np.zeros((BOARD_SIZE, BOARD_SIZE), np.uint8)         # Makes a black 500×500 picture with one channel
        
        for (r, c) in members:                                      # loop sets the 100×100 area of each tile in the group to 255 (white)
            mask[r * TILE_SIZE:(r + 1) * TILE_SIZE,
                 c * TILE_SIZE:(c + 1) * TILE_SIZE] = 255
        color = CROWN_COLOR if is_crown(name) else GROUP_COLORS.get(name, (255, 255, 255))      # Picks the group color. Crowns get the magenta CROWN_COLOR. Other types get their color from GROUP_COLORS
        tint[mask > 0] = color                                                                  # Paints every pixel where the mask is white in that color
        prepared.append((members, mask, color))                                                 # Saves the three things for pass 2

    vis = cv2.addWeighted(tint, TINT_ALPHA, base, 1 - TINT_ALPHA, 0)        # Blends the two pictures: 20% of the fully colored tint plus 80% of the original photo

    # Pass 2: outlines and badges on top
    kernel = np.ones((2 * OUTLINE_INSET + 1, 2 * OUTLINE_INSET + 1), np.uint8)              # Makes a 7×7 block of ones
    for members, mask, color in prepared:                                                   # It goes through the saved list of groups
        inset = cv2.erode(mask, kernel)                                                     # Shrinks the white area by 3 pixels on every side
        contours, _ = cv2.findContours(inset, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)      # Finds the outline of the white shape
        cv2.drawContours(vis, contours, -1, color, 2, cv2.LINE_AA)                          # Draws the outline of a group

        # Badge on the tile of the group closest to the group's center
        cr = sum(r for r, _ in members) / len(members)                              # average row to get the center
        cc = sum(c for _, c in members) / len(members)                              # average column to get the center
        r, c = min(members, key=lambda m: (m[0] - cr) ** 2 + (m[1] - cc) ** 2)      # Picks the member tile closest to that center, by squared distance
        cx = c * TILE_SIZE + TILE_SIZE // 2                                         # Are the pixels x koordinate for the center of that tile
        cy = r * TILE_SIZE + TILE_SIZE // 2                                         # Are the pixels y koordinate for the center of that tile

        cv2.circle(vis, (cx, cy), BADGE_RADIUS, color, -1, cv2.LINE_AA)         # Draw a filled circle in the group color
        cv2.circle(vis, (cx, cy), BADGE_RADIUS, (0, 0, 0), 1, cv2.LINE_AA)      # Adds a black edge
        put_text_centered(vis, str(len(members)), cx, cy, 0.6)                  # Writes the number of tiles in black, centered on the circle

    return vis      # Returns the bleded picture


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

# main is the is the function that runs the entire program
def main():

    # Create the folder if missing, and delete everything inside
    prepare_folder(BLURRED_DIR)
    prepare_folder(TILE_DIR)
    prepare_folder(CLASSIFIED_DIR)
    prepare_folder(GROUPED_DIR)

    files = sorted(glob.glob(IMAGE_PATTERN)) # Finds and sorts .jpg in the original picture folder 

    # Step 1: blur
    for f in files: # Goes through the list of pictures
        blurred = mean_blur_image(f, KERNEL_SIZE) # Calls the function to blur pictuers and saves them in blurred
        cv2.imwrite(os.path.join(BLURRED_DIR, os.path.basename(f)), blurred) # Saves the blurred pictures in the blurred pictuers folder
        print(f"[BLUR] {os.path.basename(f)}") # Prints the progress in the terminal

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