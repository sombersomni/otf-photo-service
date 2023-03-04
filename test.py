import torch
import torchvision.transforms as T
from torchvision.models.detection import fasterrcnn_resnet50_fpn
import cv2
import os
from typing import Tuple
from PIL import Image, ImageDraw

def smart_crop(user_box: Tuple[int,int,int,int]):
    filename = os.path.join('data', 'nba_small.jpg')
    output_file = os.path.join('data', 'cropped.jpg')
    output_bbox = os.path.join('data', 'bbox.jpg')

    # Load the pre-trained Faster R-CNN model
    model = fasterrcnn_resnet50_fpn(weights=True)
    model.eval()

    # Load the input image
    image = Image.open(filename)

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
    padding = 0.1
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
    cropped_image = image.crop((xmin, ymin, xmax, ymax))

    # Resize the cropped image to fit within the user-specified bounding box
    user_width = user_box[2]
    user_height = user_box[3]
    aspect_ratio = user_width / user_height
    cropped_width = cropped_image.width
    cropped_height = cropped_image.height
    cropped_aspect_ratio = cropped_width / cropped_height
    if cropped_aspect_ratio > aspect_ratio:
        new_height = int(user_width / cropped_aspect_ratio)
        resized_image = cropped_image.resize((user_width, new_height))
        padding = (user_height - new_height) // 2
        resized_image = Image.new('RGB', (user_width, user_height), (255, 255, 255))
        resized_image.paste(cropped_image, (0, padding))
    else:
        new_width = int(user_height * cropped_aspect_ratio)
        resized_image = cropped_image.resize((new_width, user_height))
        padding = (user_width - new_width) // 2
        resized_image = Image.new('RGB', (user_width, user_height), (255, 255, 255))
        resized_image.paste(cropped_image, (padding, 0))

    # Save the resized image
    resized_image.save(output_file)

    # Draw bounding boxes over the original image
    draw = ImageDraw.Draw(image)
    for box in boxes:
        xmin, ymin, xmax, ymax = box
        draw.rectangle([(xmin, ymin), (xmax, ymax)], outline=(0, 255, 0))

    # Draw the user-specified bounding box over the original image
    xmin, ymin, xmax, ymax = user_box
    draw.rectangle([(xmin, ymin), (xmax, ymax)], outline=(255, 0, 0))

    # Save the image with bounding boxes drawn
    image.save(output_bbox)
    image.close()

smart_crop((0, 0, 400, 300))