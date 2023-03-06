from io import BytesIO
from typing import Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont


class ImageProcessor:
    @staticmethod
    def smart_crop(image: Image):
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
    def resize_image(replacement_img: Image, original_size: Tuple[int, int], keep_aspect_ratio=False) -> Image:
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
    def text_img_generator(
        original_img: Image,
        text: str,
        font_type: bytes,
        font_size: float | int,
        padding: Tuple[int, int] = (2,1)):
        import cv2
        # Load the image
        gray = cv2.imdecode(original_img.tobytes(), cv2.IMREAD_GRAYSCALE)

        # Apply thresholding to extract the letters
        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # Find the contours of the letters
        contours, hierarchy = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Get the bounding boxes of the letters
        boxes = (cv2.boundingRect(c) for c in contours)

        # Calculate the width and height of each letter
        sizes = [(w, h) for x, y, w, h in boxes]

        # Calculate the maximum number of letters that can fit on a single line
        max_letters_per_line = int(original_img.shape[1] / max(sizes, key=lambda x: x[0])[0])
        print('max letters per line', max_letters_per_line)
        num_lines = len(text) / max_letters_per_line
        new_img_height = int((max(sizes, key=lambda x: x[1])[1] + padding[1]) * num_lines)
        print('new img height', new_img_height)
        # Create a new image with the same dimensions as the original image
        new_img = Image.new('RGB', (original_img.shape[1] + padding[0], new_img_height), color=(255, 255, 255))

        # Draw the text onto the new image, adding line breaks as necessary
        draw = ImageDraw.Draw(new_img)

        font = ImageFont.truetype(font_type, size=font_size)

        x, y = 0, 0

        for word in text.split():
            word_width, _ = draw.textsize(word, font=font)
            
            if x + word_width >= original_img.shape[1]:
                x = 0
                y += max(sizes, key=lambda x: x[1])[1]
                
            draw.text((x, y), word, font=font, fill=(0, 0, 0))
            
            x += word_width + draw.textsize(' ', font=font)[0]

        # Save the new image
        return new_img