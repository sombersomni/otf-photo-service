from io import BytesIO
from typing import Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont

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
       "name": font['Name'].value,
       "size": style_sheet['FontSize'],
       "affineTransform": layer.transform,
       "data": style_sheet,
    }

class ImageProcessor:
    @staticmethod
    def smart_crop(image):
        import torch
        import torchvision.transforms as T
        from torchvision.models.detection import (
            fasterrcnn_resnet50_fpn,
            FasterRCNN_ResNet50_FPN_Weights
        )
        # Load the pre-trained Faster R-CNN model
        model = fasterrcnn_resnet50_fpn(weights=FasterRCNN_ResNet50_FPN_Weights.DEFAULT)
        model.eval()

        # Convert the image to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Define the transformations to be applied to the image
        transform = T.Compose([T.ToTensor()])

        # Apply the transformations to the image
        image_tensor = transform(image)

        # Run the model to detect objects in the image
        with torch.no_grad():
            output = model([image_tensor])

        # Extract the bounding boxes and class labels from the output
        boxes = output[0]['boxes'].numpy()
        scores = output[0]['scores'].numpy()

        # Select the bounding box corresponding to the main object in the image
        main_box = None
        max_score = 0
        for i in range(len(boxes)):
            if scores[i] > max_score:
                max_score = scores[i]
                main_box = boxes[i]

        # Add padding to the selected bounding box
        padding = 0.2
        xmin, ymin, xmax, ymax = main_box
        width = xmax - xmin
        height = ymax - ymin
        xmin -= padding * width
        xmax += padding * width
        ymin -= padding * height
        ymax += padding * height

        # Crop the image using the selected bounding box and the added padding
        xmin = max(int(xmin), 0)
        ymin = max(int(ymin), 0)
        xmax = min(int(xmax), image.width)
        ymax = min(int(ymax), image.height)
        print('first crop bbox', (xmin, ymin, xmax, ymax))
        cropped_image = image.crop((xmin, ymin, xmax, ymax))
        print('cropped bbox', cropped_image.getbbox())
        return cropped_image

    @staticmethod
    def resize_image(replacement_img, original_size, keep_aspect_ratio=False):
        print('Image Processor resize is starting...')
        # Get the sizes and aspect ratios of the original and replacement images
        orig_width, orig_height = original_size
        orig_aspect_ratio = orig_width / orig_height

        repl_width, repl_height = replacement_img.size
        repl_aspect_ratio = repl_width / repl_height

        # Check if the two images have the same width and height
        if orig_width == repl_width and orig_height == repl_height:
            return replacement_img

        # Check if the aspect ratios of the two images are the same
        if orig_aspect_ratio == repl_aspect_ratio:
            # Make the replacement image large enough to match the width and height of the original image
            return replacement_img.resize((orig_width, orig_height), resample=Image.LANCZOS)

        if keep_aspect_ratio:
            orig_area = orig_width * orig_height
            repl_area = repl_width * repl_height
            area_ratio = orig_area / repl_area
            new_size = (int(repl_width * area_ratio) + 1, int(repl_height * area_ratio) + 1)
            replacement_img = replacement_img.resize(new_size, resample=Image.LANCZOS)
            return replacement_img
        # If the aspect ratios are different, then we paste the replacement image in the center of the original image
        # bounding box and resize the replacement image until it covers the bounding box area
        width_ratio = orig_width / repl_width
        height_ratio = orig_height / repl_height

        if width_ratio > height_ratio:
            print(width_ratio, 'width ratio wins')
            # Scale up the replacement image until its area is close to the original image's area
            new_size = (int(repl_width * width_ratio), int(repl_height * width_ratio))
            replacement_img = replacement_img.resize(new_size, resample=Image.LANCZOS)
        elif height_ratio > width_ratio:
            print(height_ratio, 'height ratio wins')
            # Scale down the replacement image until its area is close to the original image's area
            new_size = (int(repl_width * height_ratio), int(repl_height * height_ratio))
            replacement_img = replacement_img.resize(new_size, resample=Image.LANCZOS)

        # Calculate the coordinates to paste the replacement image at the center of the original image
        paste_coords = ((orig_width - replacement_img.width) // 2, (orig_height - replacement_img.height) // 2)

        # Create a new image and paste the replacement image onto it at the calculated coordinates
        new_img = Image.new(mode='RGB', size=(orig_width, orig_height), color=(255, 255, 255))
        new_img.paste(replacement_img, paste_coords)

        return new_img
    
    @staticmethod
    def replicate_text_image(
        layer,
        text,
        padding = 4,
        line_break=False,
        font_format='pt',
        dpi=72
    ):
        # recompute font size to pixels
        # we can expect the format to be in pt (point) for now
        text_data = get_text_data(layer)
        print('layer size', layer.size)
        print(type(text_data['name']))
        font_name = text_data['name'].replace('\'', '')
        print(font_name)
        font_type = open(f"data/ArialMT.ttf", 'rb')
        # use the affine transform vertical scale for now
        affineTransform = text_data['affineTransform']
        font_size = (
            int(text_data['size'] * affineTransform[3])
        )
        # Load the image
        print(len(layer.text.replace(' ', '')))
        letter_width = font_size / len(layer.text.replace(' ', ''))
        print('font size', font_size)
        print('letter width', letter_width)
        max_letters_per_line = int(layer.size[0] / letter_width)
        print('max letters per line', max_letters_per_line)
        num_lines = int(len(text) / max_letters_per_line) if max_letters_per_line > 0 else 0
        print('predicted num of lines', num_lines)
        new_img_height = int(layer.size[1] * num_lines)
        print('new img height', new_img_height)
        # Create a new image with the same dimensions as the original image
        new_img = Image.new('RGBA', (layer.width, layer.height), color=(0,0,0,0))

        # Draw the text onto the new image, adding line breaks as necessary
        draw = ImageDraw.Draw(new_img)
        font = ImageFont.truetype(font_type, size=font_size)

        x, y = 0, 0
        word_positions = []
        word_sizes = []
        for word in text.split():
            word_width, word_height = draw.textsize(word, font=font)
            word_sizes.append((word_width, word_height))
            if line_break and x + word_width >= layer.size[0]:
                    x = 0
                    y += word_height + padding
            word_positions.append((x, y))
            x += word_width + draw.textsize(' ', font=font)[0]
        max_word_height = max([height for _, height in word_sizes])
        print('max word height', max_word_height)
        print(list(zip(word_positions, text.split())))
        new_img = Image.new('RGBA', (layer.width + padding * 2, layer.height + padding * 2), color=(0,0,0,0))
        # Draw the text onto the new image, adding line breaks as necessary
        draw = ImageDraw.Draw(new_img)
        for position, word in zip(word_positions, text.split()):
            draw.text(position, word, font=font, fill=(255,255,255))   
        # new_img = new_image.rotate(angle, expand=True)
        # dx, dy = random.randint(-10, 10), random.randint(-10, 10)
        # the sheer positions are b and d
        # a and e are scale
        # c, f are for position

        # (TODO): Try a new transform to center the image
        print(affineTransform)
        a, b, c, d, e, f = affineTransform
        pillow_transform = (2, c * -.5, -5, b * -.5, 2, -5)
        transformed_img = new_img.transform(new_img.size, Image.AFFINE, pillow_transform)
        # transformed_img = new_img.transform(new_img.size, Image.AFFINE,(
        #     -1 * (affineTransform),
        #     -1 * (affineTransform[2] / affineTransform[0]),
        #     -1 * padding  - (affineTransform[2] / affineTransform[0]),
        #     -1 * (affineTransform[1] / affineTransform[3]),
        #     1,  
        #     -1 * padding - (affineTransform[1] / affineTransform[3])
        # ))
        font_type.close()
        # Save the new image
        return transformed_img