import torch
import torchvision.transforms as T
from torchvision.models.detection import (
    fasterrcnn_resnet50_fpn,
    FasterRCNN_ResNet50_FPN_Weights
)
import os
from typing import Tuple
from PIL import Image, ImageDraw

def smart_crop(user_box: Tuple[int,int,int,int]):
    filename = os.path.join('data', 'nba_small.jpg')
    output_file = os.path.join('data', 'cropped.jpg')
    output_bbox = os.path.join('data', 'bbox.jpg')

    # Load the pre-trained Faster R-CNN model
    model = fasterrcnn_resnet50_fpn(weights=FasterRCNN_ResNet50_FPN_Weights.DEFAULT)
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

    # Get the user-specified bounding box
    user_box = (0, 0, 400, 300)

    # Calculate the size of the bounding box that fits within the cropped image
    cropped_width, cropped_height = cropped_image.size
    box_aspect_ratio = user_box[2] / user_box[3]
    cropped_aspect_ratio = cropped_width / cropped_height
    if cropped_aspect_ratio > box_aspect_ratio:
        box_width = int(user_box[3] * cropped_aspect_ratio)
        box_height = user_box[3]
    else:
        box_width = user_box[2]
        box_height = int(user_box[2] / cropped_aspect_ratio)

    # Calculate the coordinates of the bounding box within the cropped image
    box_left = (cropped_width - box_width) // 2
    box_top = (cropped_height - box_height) // 2
    box_right = box_left + box_width
    box_bottom = box_top + box_height

    # Crop the image again using the new bounding box
    centered_image = cropped_image.crop((box_left, box_top, box_right, box_bottom))

    # Resize the centered image to fit within the user-specified bounding box
    resized_image = centered_image.resize(user_box[2:])

    # Save the resized image
    resized_image.save(output_file)

    # Draw bounding boxes over the original image
    draw = ImageDraw.Draw(image)
    for box in boxes:
        xmin, ymin, xmax, ymax = box
        draw.rectangle([(xmin, ymin), (xmax, ymax)], outline=(0, 255, 0))

    # Draw the bounding box corresponding to the main object in the image
    xmin, ymin, xmax, ymax = main_box
    draw.rectangle([(xmin, ymin), (xmax, ymax)], outline=(255, 0, 0))

    # Draw the bounding box that fits within the cropped image
    box_left += xmin
    box_top += ymin
    box_right += xmin
    box_bottom += ymin
    draw.rectangle([(box_left, box_top), (box_right, box_bottom)], outline=(0, 0, 255))

    # Draw the bounding box that was resized to fit within the user-specified bounding box
    xmin, ymin, xmax, ymax = (0, 0, resized_image.width, resized_image.height)
    draw.rectangle([(xmin, ymin), (xmax, ymax)], outline=(255, 255, 0))
    image.save(output_bbox)
    image.close()

smart_crop((0, 0, 400, 300))