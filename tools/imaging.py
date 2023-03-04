import torch
import torchvision.transforms as T
from torchvision.models.detection import fasterrcnn_resnet50_fpn
import cv2
import os

def smart_crop():
    filename = os.path.join('data', 'player.jpg')
     # Load the pre-trained Faster R-CNN model
    model = fasterrcnn_resnet50_fpn(pretrained=True)
    model.eval()
    # Load the input image
    image = cv2.imread(filename)

    # Convert the image from BGR to RGB
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

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
    xmax = min(int(xmax), image.shape[1])
    ymax = min(int(ymax), image.shape[0])
    cropped_image = image[ymin:ymax, xmin:xmax]

    # Save the cropped image
    cv2.imwrite('data/cropped_image.png', cropped_image)