"""
Mean blur of all pictures in a folder using OpenCV.

Reads every .jpg in "Cropped and perspective corrected boards",
applies a mean (box) blur, and saves the result in the subfolder
"Blurred Pictures". The subfolder is emptied every time the program starts.
"""

import cv2
import glob
import os
import shutil

# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------

IMAGE_DIR = "Cropped and perspective corrected boards"
BLURRED_DIR = os.path.join(IMAGE_DIR, "Blurred Pictures")
IMAGE_PATTERN = os.path.join(IMAGE_DIR, "*.jpg")

KERNEL_SIZE = (30, 30)  # mean blur window (width, height). Bigger = more blur


# ----------------------------------------------------------------------
# FUNCTIONS
# ----------------------------------------------------------------------

def prepare_blurred_folder(folder=BLURRED_DIR):
    """Create the folder if missing, and delete everything inside it."""
    os.makedirs(folder, exist_ok=True)
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if os.path.isfile(path) or os.path.islink(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
    print(f"[INFO] Cleared folder: {folder}")


def mean_blur_image(image_path, kernel_size=KERNEL_SIZE):
    """Load an image and return it with a mean blur applied."""
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Could not read image: {image_path}")
    return cv2.blur(img, kernel_size)


# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

def main():
    prepare_blurred_folder()

    files = sorted(glob.glob(IMAGE_PATTERN))
    if not files:
        print(f"[WARN] No .jpg images found in '{IMAGE_DIR}'")
        return

    for f in files:
        blurred = mean_blur_image(f)
        out_path = os.path.join(BLURRED_DIR, os.path.basename(f))
        cv2.imwrite(out_path, blurred)
        print(f"[OK] {os.path.basename(f)} -> {out_path}")

    print(f"\nDone. Blurred {len(files)} images with kernel {KERNEL_SIZE}.")


if __name__ == "__main__":
    main()