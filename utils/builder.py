import pyocr.builders


class Builder(pyocr.builders.TextBuilder):
    def __init__(self, whitelist: str = "0123456789,", tesseract_layout: int = 6):
        super(Builder, self).__init__(tesseract_layout)
        self.tesseract_configs += ["-c", "tessedit_char_whitelist=" + whitelist]
