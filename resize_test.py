import psd_tools
from PIL import Image
from lib.image_processor import ImageProcessor
from helpers.psd_layers import flatten_layers


# psd_file = psd_tools.PSDImage.open('data/nba-quarter-1080x1920.psd')
# # Get the layer information from the PSD file
# par = psd_file.image_resources.get(psd_tools.constants.Resource.PIXEL_ASPECT_RATIO)
# print(psd_file.depth)
# print(par.name, par.data)
# layers = list(flatten_layers(psd_file))
# text_layer = [layer for layer in layers if layer.name == 'Period Title'][-1]
# original_img = text_layer.topil()
with open('data/boxed-text-test.png', 'rb') as file:
  original_img = Image.open(file)

  with open('data/Arial.otf', 'rb') as font_type:
    original_img.show()
    # img = ImageProcessor.text_img_generator(original_img, 'BOTTLE WATER IS BAD', font_type, 72, padding=5, dpi=72)
    # img.save('data/output-text.png')
# text_layer = [layer for layer in layers if layer.name == 'Home Score'][-1]
# original_img = text_layer.topil()
# original_img.save('data/input-text-num.png')
# with open('data/Druk-Heavy-Trial.otf', 'rb') as font_type:
#   img = ImageProcessor.text_img_generator(original_img, '123', font_type, 66, 5)
#   img.save('data/output-text-num.png')