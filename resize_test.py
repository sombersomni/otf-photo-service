import psd_tools
import time
from PIL import Image
from lib.image_processor import ImageProcessor
from helpers.psd_layers import flatten_layers

def get_text_data(layer):
    # Extract font for each substring in the text.
    font_set = layer.resource_dict['FontSet']
    run_data = layer.engine_dict.get('StyleRun', {}).get('RunArray', [])
    style_sheets = [style.get('StyleSheet', {}).get('StyleSheetData', {}) for style in run_data]
    if len(style_sheets) == 0:
        raise Exception("No style sheets found")
    style_sheet = style_sheets[0]
    font_index = style_sheet.get('Font')
    font = font_set[font_index]
    return {
       "name": font['Name'],
       "size": style_sheet['FontSize'],
       "affineTransform": layer.transform,
       "data": style_sheet,
    }

psd_file = psd_tools.PSDImage.open('data/text-style-test_2.psd')
# Get the layer information from the PSD file
par = psd_file.image_resources.get(psd_tools.constants.Resource.PIXEL_ASPECT_RATIO)
print(psd_file.depth)
print(par.name, par.data)
layers = list(flatten_layers(psd_file))
text_layers = [layer for layer in layers if layer.kind == 'type'][:5]
for text_layer in text_layers:
    print(text_layer.name)
    text_layer.topil().show()
    time.sleep(2)
    psd_size = psd_file.size
    img = ImageProcessor.replicate_text_image(text_layer, text_layer.text, psd_size, padding=2, dpi=300)
    img.show()
    time.sleep(2)