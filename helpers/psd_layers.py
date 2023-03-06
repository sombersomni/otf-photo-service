from numbers import Number
from typing import Iterable, Tuple
from PIL import Image
import psd_tools

from constants import Title_Image_Zip

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
    replacement_images: Iterable[Title_Image_Zip],
    replacement_layer_map: dict[str, psd_tools.api.layers.Layer]
):
    """
    Resize the replacement image to fit within the bounds of the layer
    """

    for title, replacement_image in replacement_images:
        layer_to_replace = replacement_layer_map[title]
        width_ratio = replacement_image.width / layer_to_replace.width
        height_ratio = replacement_image.height / layer_to_replace.height
        if width_ratio > height_ratio:
            new_width = layer_to_replace.width
            new_height = int(replacement_image.height * (new_width / replacement_image.width))
        else:
            new_height = layer_to_replace.height
            new_width = int(replacement_image.width * (new_height / replacement_image.height))
        resized_image = replacement_image.resize((
            layer_to_replace.width if 'Getty' in title else new_width,
            layer_to_replace.height if 'Getty' in title else new_height
        ))
        print(title, resized_image.width, resized_image.height)
        yield Title_Image_Zip(title, resized_image)

def bulk_layer_composites(
    layers: Iterable[psd_tools.api.layers.Layer],
    replacement_images: Iterable[Title_Image_Zip],
    filesize: Tuple[Number, Number]
):
    visible_layers = (layer for layer in layers if layer.is_visible())
    replace_image_map = {title: image for title, image in replacement_images}
    for layer in visible_layers:
        print(layer.name, layer.kind)
        layer_image = Image.new(mode='RGBA', size=filesize, color=(0, 0, 0, 0))
        layer_data = layer.composite()
        replacement_image = replace_image_map.get(layer.name)
        layer_image.paste(
            replacement_image if replacement_image else layer_data,
            box=layer.bbox[:2],
            mask=None if replacement_image else layer_data
        )
        yield layer_image

