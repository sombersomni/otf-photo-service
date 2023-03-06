from PIL import Image
from lib.image_processor import ImageProcessor

original_img = Image.open('data/getty-original.jpeg')
new_img = Image.open('data/cropped_img.png')
img = ImageProcessor.resize_image(new_img, original_img.size, keep_aspect_ratio=False)
img.save('data/final_getty.png')
img.close()