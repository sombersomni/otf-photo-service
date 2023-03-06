from PIL import Image
from lib.imaging import smart_crop, replace_image

original_img = Image.open('data/dribble.jpg')
new_img = Image.open('data/jook.jpg')
cropped_img = smart_crop(new_img, original_img.getbbox())
img = replace_image(original_img, new_img)
img.save('data/final.png')