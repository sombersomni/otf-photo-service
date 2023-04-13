from numbers import Number
from typing import Iterable, Tuple
from PIL import Image
import psd_tools

from constants import Title_Image_Zip
from lib.image_processor import ImageProcessor

def flatten_layers(psd):
    """
    Flatten layers for psd file
    """
    for layer in psd.descendants():
        if layer.is_group():
            flatten_layers(layer)
        else:
            yield layer

def bulk_resize_images(
    replacement_images,
    replacement_layer_map
):
    """
    Resize the replacement image to fit within the bounds of the layer
    """

    for title, replacement_image in replacement_images:
        layer_to_replace = replacement_layer_map[title]
        
        resized_image = ImageProcessor.resize_image(
            replacement_image,
            (layer_to_replace.width, layer_to_replace.height),
            keep_aspect_ratio='Logo' in title
        )
        print(title, resized_image.width, resized_image.height)
        yield Title_Image_Zip(title, resized_image)

def bulk_replicate_text(text_layers, psd_size, font_type_map, text_value_map):
    for layer in text_layers:
        text = text_value_map.get(layer.name)
        replicated_image = ImageProcessor.replicate_text_image(layer, text, psd_size, font_type_map)
        yield Title_Image_Zip(layer.name, replicated_image)

def bulk_layer_composites(
    layers,
    replacement_images,
    filesize
):
    replace_image_map = {title: image for title, image in replacement_images}
    for layer in layers:
        print('Replicate text')
        print(layer.name, layer.kind)
        print(layer.bbox)
        print('---------------')
        layer_image = Image.new(mode='RGBA', size=filesize, color=(0, 0, 0, 0))
        layer_data = layer.composite()
        replacement_image = replace_image_map.get(layer.name)
        layer_image.paste(
            replacement_image if replacement_image else layer_data,
            box=layer.bbox[:2],
            mask=None if replacement_image else layer_data
        )
        yield layer_image

