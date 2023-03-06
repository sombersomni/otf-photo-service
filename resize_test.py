import psd_tools
from PIL import Image
from lib.image_processor import ImageProcessor
from helpers.psd_layers import flatten_layers


psd_file = psd_tools.PSDImage.open('data/nba-quarter-1080x1920.psd')
# Get the layer information from the PSD file
layers = list(flatten_layers(psd_file))
text_layer = [layer for layer in layers if layer.name == 'Period Title'][-1]
original_img = text_layer.topil()
original_img.save('data/input-text.png')
with open('data/Druk-Medium-Trial.otf', 'rb') as font_type:
  img = ImageProcessor.text_img_generator(original_img, 'END 3', font_type, 87, (2,1))
  img.save('data/output-text.png')