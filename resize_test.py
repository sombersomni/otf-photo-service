import psd_tools
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

psd_file = psd_tools.PSDImage.open('data/nba-quarter-1080x1920.psd')
# Get the layer information from the PSD file
par = psd_file.image_resources.get(psd_tools.constants.Resource.PIXEL_ASPECT_RATIO)
print(psd_file.depth)
print(par.name, par.data)
layers = list(flatten_layers(psd_file))
text_layer = [layer for layer in layers if layer.name == 'Period Title'][-1]
a = (1,2,3,4,5,6)
print(a[:4])
ImageProcessor.replicate_text_image(text_layer, 'END 4', padding=5, dpi=72)