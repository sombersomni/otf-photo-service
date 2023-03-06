import unittest
from PIL import Image
from lib.image_processor import ImageProcessor

class TestImageProcessor(unittest.TestCase):

    def test_resize_image(self):
        # create a new image for testing
        img = Image.new('RGB', (100, 50), color='red')
        # set the desired bounding box
        bounding_box = (80, 40)
        # call the static method of the ImageProcessor class
        resized_img = ImageProcessor.resize_image(img, bounding_box)
        # assert that the resized image has the expected width and height
        self.assertEqual(resized_img.size, bounding_box)

    def test_resize_image_same_size(self):
        # create a new image for testing
        img = Image.new('RGB', (50, 50), color='red')
        # set the desired bounding box
        bounding_box = (50, 50)
        # call the static method of the ImageProcessor class
        resized_img = ImageProcessor.resize_image(img, bounding_box)
        # assert that the resized image has the expected width and height
        self.assertEqual(resized_img.size, bounding_box)

    def test_resize_image_same_ratio(self):
        # create a new image for testing
        img = Image.new('RGB', (50, 50), color='red')
        # set the desired bounding box
        bounding_box = (40, 40)
        # call the static method of the ImageProcessor class
        resized_img = ImageProcessor.resize_image(img, bounding_box)
        # assert that the resized image has the expected width and height
        self.assertEqual(resized_img.size, bounding_box)


if __name__ == '__main__':
    unittest.main()
