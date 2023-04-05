from collections import namedtuple


Key_Title_Zip = namedtuple('KeyTitleZip', ['bucket_key', 'layer_title'])
Key_Font_Zip = namedtuple('KeyFontZip', ['bucket_key', 'font_name'])
Title_Image_Zip = namedtuple('TitleImageZip', ['layer_title', 'image'])
Title_Font_Zip = namedtuple('TitleFontZip', ['font_title', 'font_bytes'])