from PIL import Image
from lib.imaging import replace_image

original_img = Image.open('data/atlanta-hawks.png')
new_img = Image.open('data/houston-rockets.png')
img = replace_image(original_img, new_img, keep_aspect_ratio=True)
img.save('data/final.png')
img.close()