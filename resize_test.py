from PIL import Image
from lib.image_processor import ImageProcessor

original_img = Image.open('data/getty-original.jpeg')
new_img = Image.open('data/cropped_img.png')
img = ImageProcessor.text_img_generator(original_img, '44')