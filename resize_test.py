import psd_tools
from PIL import Image
from lib.image_processor import ImageProcessor
from helpers.psd_layers import flatten_layers


psd_file = psd_tools.PSDImage.open('data/nba-quarter-1080x1920.psd')
# Get the layer information from the PSD file
par = psd_file.image_resources.get(psd_tools.constants.Resource.PIXEL_ASPECT_RATIO)
print(psd_file.depth)
print(par.name, par.data)
layers = list(flatten_layers(psd_file))
text_layer = [layer for layer in layers if layer.name == 'Period Title'][-1]
original_img = text_layer.topil()
original_img.save('data/input-text.png')
with open('data/Druk-Medium-Trial.otf', 'rb') as font_type:
  img = ImageProcessor.text_img_generator(original_img, 'END 3', font_type, 78, 5)
  img.save('data/output-text.png')