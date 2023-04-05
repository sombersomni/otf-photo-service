from io import BytesIO
from typing import Tuple
import numpy as np
import math
from PIL import Image, ImageDraw, ImageFont, ImageOps

def find_image_bounding_box(img):
    left = img.width
    top = img.height
    right = bottom = 0
    for x in range(img.width):
        for y in range(img.height):
            if img.getpixel((x, y))[-1] != 0:
                if x < left:
                    left = x
                if y < top:
                    top = y
                if x > right:
                    right = x
                if y > bottom:
                    bottom = y

    # Calculate the bounding box
    x = left
    y = top
    w = right - left + 1
    h = bottom - top + 1
    return x, y, x + w - 1, y + h - 1

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
    fill_color_values = style_sheet['FillColor']['Values']
    fill_color_rgb = tuple(int(color * 255) for color in fill_color_values[1:])
    return {
       "name": font['Name'].value,
       "size": int(style_sheet['FontSize']),
       "affineTransform": layer.transform,
       "data": style_sheet,
       "tracking": int(style_sheet.get('Tracking', 20)),
       "fillColor": fill_color_rgb,
       "allCaps": int(style_sheet.get('FontCaps', 0)) == 2, # 2 means its all caps
       "leading": int(style_sheet.get('Leading', 20)),
       "underline": style_sheet['Underline']
    }


# Step 1: Extract the affine transform values from the psd-tools object
# Assuming you have already extracted the layer and have the transform values
# transform_values = (a, b, c, d, e, f)

# Step 2: Convert the affine transformation values into a 3x3 transformation matrix
def create_matrix(transform_values):
    a, b, c, d, e, f = transform_values
    return np.array([[a, b, 0], [c, d, 0], [e, f, 1]])


# Step 4: Convert the 3x3 matrix into a format that Pillow can use
def convert_matrix_to_pillow(matrix):
    # return (matrix[0, 0], matrix[0, 1], matrix[2, 0], matrix[1, 0], matrix[1, 1], matrix[2, 1])
    return (matrix[0, 0], matrix[0, 1] * -1, matrix[2, 0], matrix[1, 0] * -1, matrix[1, 1], matrix[2, 1])


def get_text_bounding_box(image):
    width, height = 300, 900
    image_np = np.asarray(image)
    height, width, _ = image_np.shape
    print(image_np.shape)
    left = width
    right = 0
    top = height
    bottom = 0
    
    for y in range(height):
        for x in range(width):
            # Check if the pixel is not transparent (alpha != 0)
            if image_np[y, x, 3] != 0:
                left = min(left, x)
                right = max(right, x)
                top = min(top, y)
                bottom = max(bottom, y)
    
    # Add a little padding to the bounding box
    padding = 2
    left = max(0, left - padding)
    right = min(width, right + padding)
    top = max(0, top - padding)
    bottom = min(height, bottom + padding)
    return left, top, right, bottom


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
        psd_size,
        font_type_map,
        **kwargs
    ):
        import cv2
        # recompute font size to pixels
        # we can expect the format to be in pt (point) for now
        padding = kwargs.get("padding", 1)
        bound_text = kwargs.get("bound_text", False)
        psd_width, psd_height = psd_size
        text_data = get_text_data(layer)
        print('layer size', layer.size)
        if text_data['allCaps']:
            text = text.upper()
        font_name = text_data['name'].replace('\'', '')
        print(font_name)
        # use the affine transform vertical scale for now
        affine_transform = text_data['affineTransform']
        font_size = int(text_data['size'])
        font_fill_color = text_data['fillColor']
        font_leading = text_data['leading']
        print('font_size', font_size)
        font_tracking = text_data['tracking'] * ((font_size / 72) / 20)
        print('font_tracking', font_tracking)
        original_img = layer.topil()
        # Create a new image with the same dimensions as the original image
        new_img = Image.new('RGBA', psd_size, color=(0,0,0,0))
        new_img.paste(original_img)
        # Realign original text image horizontally
        a, b, c, d, e, f = affine_transform
        matrix = create_matrix(affine_transform)
        # pillow_transform = (.5, c * -.5, -5, b * -.5, .5, -5)
        # Create translation matrix
        translation_matrix = np.array([[1,0,0],[0,1,0],[e,f, 1]])
        # Compute the QR decomposition of the matrix
        Q, R = np.linalg.qr(matrix[:2, :2])

        # Extract the upper triangular matrix
        shear_matrix = (R * (np.diag(R) ** -1))
        # Negate the sheering
        shear_matrix = np.array([
            [shear_matrix[0,0], shear_matrix[0,1] * -1, 0],
            [shear_matrix[1,0] * -1, shear_matrix[1,1], 0],
            [0,0,1]
        ])
        # Extract the rotation angle from the affine transformation matrix
        rotation_angle = math.degrees(math.atan2(c, a))
        # Create the rotation matrix
        theta = math.radians(rotation_angle)
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        rotation_matrix = np.array([
            [cos_theta, sin_theta, 0],
            [-sin_theta, cos_theta, 0],
            [0,0,1]
        ]) 
        transformation_matrix = rotation_matrix @ translation_matrix
        inv_matrix = np.linalg.inv(transformation_matrix)
        pillow_transform = convert_matrix_to_pillow(inv_matrix @ shear_matrix)
        # Create the sheering matrix
        transformed_img = new_img.transform(new_img.size, Image.AFFINE, pillow_transform)
        # Scan the image to find the bounding box of the text
        original_bbox = find_image_bounding_box(transformed_img)
        # Draw the bounding box (optional)
        draw = ImageDraw.Draw(transformed_img)
        draw.rectangle(original_bbox, outline='red')
        left, top, right, bottom = original_bbox
        text_width = right - left + 1 # add small additional padding
        # Calculate text length before drawing on canvas
        new_img = Image.new('RGBA', psd_size, color=(0,0,0,0))
        draw = ImageDraw.Draw(new_img)
        font_type = font_type_map.get(font_name)
        if font_type is None:
            print("No font type was found")
            return
        font = ImageFont.truetype(font_type, size=font_size)
        x, y = 0, 0
        word_positions = []
        word_sizes = []
        text_boundary = text_width + padding * 2 if bound_text else abs(psd_width - e) - padding * 2
        print(text_boundary, psd_width, e)
        for word in text.split():
            word_width, word_height = 0, font_size
            for i, letter in enumerate(word):
                letter_width = draw.textlength(letter, font=font)
                word_width += int(letter_width + (0 if i == len(word) - 1 or font_tracking <= 1 else font_tracking))
            word_sizes.append((word_width, word_height))
            # use temp padding of 10 until better calculation available
            if x + word_width > text_boundary:
                x = 0
                y += int(font_leading * (font_size / 72))
                print('font_leading', font_leading, word_height, int(font_leading * (font_size / 72)))

            word_positions.append((x, y))
            x += int(word_width + draw.textlength(' ', font=font))
        max_word_height = max([height for _, height in word_sizes])
        print(word_sizes)
        print('max word height', max_word_height)
        print(list(zip(word_positions, text.split())))
        # Draw text image
        for position, word in zip(word_positions, text.split()):
            x, y = position
            for letter in word:
                draw.text((x, y), letter, font=font, fill=font_fill_color)
                letter_width = draw.textlength(letter, font=font)
                x += letter_width + (0 if font_tracking > 1 else font_tracking)

        # Invert the transformation matrix, if necessary
        inv_matrix = np.linalg.inv(matrix)
        pillow_transform = convert_matrix_to_pillow(inv_matrix)
        transformed_img = new_img.transform(new_img.size, Image.AFFINE, pillow_transform)
        left, top, right, bottom = find_image_bounding_box(transformed_img)
        cropped_img = transformed_img.crop((left - padding, top - padding * 0.5, right + padding, bottom + padding * 2))
        font_type.close()
        # Save the new image
        return cropped_img