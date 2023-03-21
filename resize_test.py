import psd_tools
import time
from PIL import Image
from lib.image_processor import ImageProcessor
from helpers.psd_layers import flatten_layers

psd_file = psd_tools.PSDImage.open('data/text-style-test_2.psd')
# Get the layer information from the PSD file
par = psd_file.image_resources.get(psd_tools.constants.Resource.PIXEL_ASPECT_RATIO)
print(psd_file.depth)
print(par.name, par.data)
layers = list(flatten_layers(psd_file))
text_layers = [layer for layer in layers if layer.kind == 'type' and 'TRACK' in layer.name]
for text_layer in text_layers:
    print(text_layer.name)
    text_layer.topil().show()
    time.sleep(2)
    psd_size = psd_file.size
    img = ImageProcessor.replicate_text_image(text_layer, text_layer.text, psd_size, padding=2, dpi=300)
    img.show()
    time.sleep(2)