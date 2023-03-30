from PIL import Image, ImageOps, ImageEnhance
import cv2
import numpy as np


def cv2pil(image: cv2.Mat):
    new_image = image.copy()
    if new_image.ndim == 2:
        pass
    elif new_image.shape[2] == 3:
        new_image = cv2.cvtColor(new_image, cv2.COLOR_BGR2RGB)
    elif new_image.shape[2] == 4:
        new_image = cv2.cvtColor(new_image, cv2.COLOR_BGRA2RGBA)
    new_image = Image.fromarray(new_image)
    return new_image


def pil2cv(image: Image):
    new_image = np.array(image, dtype=np.uint8)
    if new_image.ndim == 2:
        pass
    elif new_image.shape[2] == 3:
        new_image = cv2.cvtColor(new_image, cv2.COLOR_RGB2BGR)
    elif new_image.shape[2] == 4:
        new_image = cv2.cvtColor(new_image, cv2.COLOR_RGBA2BGRA)
    return new_image


def correct(
    img: Image.Image,
    crop_range: tuple = None,
    threshold: int = 0,
    threshold_max: int = -1,
    invert: bool = True,
    scale: float = 1,
    contrast: float = 1,
    brightness: float = 1,
) -> Image.Image:
    tmp = img.crop(crop_range) if crop_range else img
    tmp = ImageOps.invert(tmp) if invert else tmp
    tmp = tmp.convert("L")
    tmp = (
        tmp.resize((round(tmp.width * scale), round(tmp.height * scale)))
        if scale != 1
        else tmp
    )
    tmp = ImageEnhance.Contrast(tmp).enhance(contrast) if contrast != 1 else tmp
    tmp = ImageEnhance.Brightness(tmp).enhance(brightness) if brightness != 1 else tmp
    if threshold == 0:
        pass
    elif threshold_max == -1:
        tmp = tmp.point(lambda x: 0 if x < threshold else x)
    else:
        tmp = tmp.point(lambda x: 0 if x < threshold else threshold_max)
    return tmp
