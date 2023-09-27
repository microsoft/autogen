# Dealing with screenshots
import json
import sys

import numpy as np

from io import BytesIO
from PIL import Image, ImageDraw


def get_screenshot(driver, width=160, height=210):
    """Return a cropped screenshot taken by the Selenium instance.

    Args:
        driver (Chrome WebDriver)
        width (int)
        height (int)
    Returns:
        PIL Image object
    """
    png_data = driver.get_screenshot_as_png()
    pil_image = Image.open(BytesIO(png_data))
    pil_image = pil_image.crop((0, 0, 320, 420)).convert("RGB")
    pil_image = pil_image.convert("RGB")
    return pil_image


def pil_to_numpy_array(pil_image):
    """Convert PIL image to a numpy array.

    Args:
        pil_image (PIL Image)
    Returns:
        numpy array of shape (height, width, 3)
        where 3 is the number of channels (RGB).
    """
    return np.array(pil_image).astype(np.float32)


def create_gif(path_prefix):
    """Create and save an animated gif based on the dumped screenshots.

    The event file is read from <path_prefix>.json, while the images are
    loaded from <path_prefix>-<step>.png

    Args:
        path_prefix (str): Something like
            data/experiments/123_unnamed/traces/test/2000-img/2000-3
            (control step 2000; episode 3)
    """
    # Read the event file
    with open(path_prefix + ".json") as fin:
        events = json.load(fin)
    # Read the image files
    images = []
    for i, event in enumerate(events):
        img = Image.open("{}-{}.png".format(path_prefix, i)).convert("RGBA")
        images.append(img)
        # Highlight the element
        if "element" in event:
            elt = event["element"]
            highlight = Image.new("RGBA", img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(highlight)
            x0 = elt["left"]
            x1 = x0 + elt["width"]
            y0 = elt["top"]
            y1 = y0 + elt["height"]
            draw.rectangle(
                [x0, y0, x1, y1], fill=(255, 0, 0, 128), outline=(0, 0, 255, 255)
            )
            del draw
            images.append(Image.alpha_composite(img, highlight))
    # Save the image file
    durations = [250] * len(images)
    durations[-1] = 1000
    images[0].save(
        path_prefix + ".gif",
        append_images=images[1:],
        save_all=True,
        loop=0,
        duration=durations,
    )


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: {} PATH_PREFIX".format(sys.argv[0]))
        print(
            "  where PATH_PREFIX is something like "
            "data/experiments/123_unnamed/traces/test/2000-img/2000-3"
        )
        exit(1)
    create_gif(sys.argv[1])
