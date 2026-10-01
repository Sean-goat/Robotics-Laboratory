import cv2
import numpy as np

def erode_manual(binary, se):
    h, w = binary.shape
    kh, kw = se.shape
    ph, pw = kh // 2, kw // 2
    out = np.zeros_like(binary)

    # Padding med 255, så kanten ikke æder objekter
    padded = np.pad(binary, ((ph, ph), (pw, pw)), constant_values=255)

    for y in range(h):
        for x in range(w):
            fits = True
            for i in range(kh):
                for j in range(kw):
                    # Kun de felter i SE, der er 1, skal passe
                    if se[i, j] == 1 and padded[y + i, x + j] == 0:
                        fits = False
                        break
                if not fits:
                    break
            out[y, x] = 255 if fits else 0
    return out

def dilate_manual(binary, se):
    h, w = binary.shape
    kh, kw = se.shape
    ph, pw = kh // 2, kw // 2
    out = np.zeros_like(binary)

    padded = np.pad(binary, ((ph, ph), (pw, pw)), constant_values=0)

    for y in range(h):
        for x in range(w):
            hit = False
            for i in range(kh):
                for j in range(kw):
                    # Mindst ét 1-felt i SE skal ramme en hvid pixel
                    if se[i, j] == 1 and padded[y + i, x + j] == 255:
                        hit = True
                        break
                if hit:
                    break
            out[y, x] = 255 if hit else 0
    return out

img = cv2.imread("dots.jpg", cv2.IMREAD_GRAYSCALE)
if img is None:
    raise FileNotFoundError("Kan ikke læse dots.jpg")

blur = cv2.GaussianBlur(img, (5, 5), 0)
bg   = cv2.GaussianBlur(img, (0, 0), 40)
diff = cv2.subtract(bg, blur)
_, binary = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

# Selvlavet structuring element (5x5 cirkel-agtig)
se = np.array([[0, 1, 1, 1, 0],
               [1, 1, 1, 1, 1],
               [1, 1, 1, 1, 1],
               [1, 1, 1, 1, 1],
               [0, 1, 1, 1, 0]], dtype=np.uint8)

eroded  = erode_manual(binary, se)
dilated = dilate_manual(binary, se)

cv2.imshow("Original | Binary | Erosion | Dilation",
           np.hstack([img, binary, eroded, dilated]))
cv2.waitKey(0)
cv2.destroyAllWindows()