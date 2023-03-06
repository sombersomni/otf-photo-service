import torch
import torchvision.transforms as T
from torchvision.models.detection import (
    fasterrcnn_resnet50_fpn,
    FasterRCNN_ResNet50_FPN_Weights
)
import os
from typing import Tuple
from PIL import Image, ImageDraw

def smart_crop(image: Image, user_box: Tuple[int,int,int,int]):
    output_file = os.path.join('data', 'cropped_img.jpg')
    output_bbox = os.path.join('data', 'bbox_img.jpg')

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
    print((box_left, box_top, box_right, box_bottom))
    print(user_box)
    # Resize the centered image to fit within the user-specified bounding box
    # resized_image = centered_image.resize(user_box[2:])

    # Save the resized image
    centered_image.save(output_file)

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
    xmin, ymin, xmax, ymax = (0, 0, centered_image.width, centered_image.height)
    draw.rectangle([(xmin, ymin), (xmax, ymax)], outline=(255, 255, 0))
    image.save(output_bbox)
    image.close()
    return centered_image

def replace_image(original_img: Image, replacement_img: Image) -> Image:
    # Get the sizes and aspect ratios of the original and replacement images
    orig_width, orig_height = original_img.size
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

    # If the aspect ratios are different, then we paste the replacement image in the center of the original image
    # bounding box and resize the replacement image until the two areas are near equal
    orig_area = orig_width * orig_height
    repl_area = repl_width * repl_height

    if repl_area < orig_area:
        # Scale up the replacement image until its area is close to the original image's area
        scale_factor = (orig_area / repl_area) ** 0.5
        new_size = (int(repl_width * scale_factor), int(repl_height * scale_factor))
        replacement_img = replacement_img.resize(new_size, resample=Image.LANCZOS)
    elif repl_area > orig_area:
        # Scale down the replacement image until its area is close to the original image's area
        scale_factor = (orig_area / repl_area) ** 0.5
        new_size = (int(repl_width * scale_factor), int(repl_height * scale_factor))
        replacement_img = replacement_img.resize(new_size, resample=Image.LANCZOS)

    # Calculate the coordinates to paste the replacement image at the center of the original image
    paste_coords = ((orig_width - replacement_img.width) // 2, (orig_height - replacement_img.height) // 2)

    # Create a new image and paste the replacement image onto it at the calculated coordinates
    new_img = Image.new(mode='RGB', size=(orig_width, orig_height), color=(255, 255, 255))
    new_img.paste(replacement_img, paste_coords)

    return new_img