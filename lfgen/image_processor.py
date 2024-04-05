import os
import rawpy
from pyvips import Image
import numpy as np
from math import tan, radians, floor

def tan_degrees(degrees):
    return tan(radians(degrees))

def restricted_fov(length, fov, new_fov):
    return round(length*tan_degrees(new_fov/2)/tan_degrees(fov/2))

class ImageProcessor:
    def __init__(self, directory, ratio, max_x, max_y, orig_fov_x, orig_fov_y, fov_x, fov_y, flip_y):
        self.directory = directory
        self.orig_fov_x, self.orig_fov_y = orig_fov_x, orig_fov_y
        self.ratio, self.fov_x, self.fov_y = ratio, fov_x, fov_y
        self.max_x, self.max_y = max_x, max_y
        self.output, self.input_height, self.input_width, self.output_height, self.output_width = None, None, None, None, None
        self.crop_left, self.crop_top, self.crop_width, self.crop_height = None, None, None, None
        self.flip_y = flip_y
    
    def _get_image(self, x, y, extension):
        filename = os.path.join(self.directory, f'{x}-{y}.{extension}')
        if extension.lower() == "nef":
            with rawpy.imread(filename) as raw:
                return Image.new_from_array(raw.postprocess())
        else:
            return Image.new_from_file(filename)

    def _get_array(self, image):
        if (self.input_height, self.input_width) != (image.height, image.width):
            warnings.warn(
                f'Inconsistent input image resolutions. '
                f'Expected {self.input_height}x{self.input_width}, '
                f'got {image.height}x{image.width}.'
            )

        # Crop the image to simulate a restricted field of view
        if self.crop_top != 0 or self.crop_left != 0:
            image = image.crop(
                self.crop_left,
                self.crop_top,
                self.crop_width,
                self.crop_height
            )
        
        # Downsample image and add image to integral image
        if self.ratio != 1:
            image = image.resize(
                self.output_width/image.width,
                vscale=self.output_height/image.height
            )
        
        if self.flip_y:
            image = image.flipver()
        
        return image

    def set_dims_and_get_array(self, x, y, extension):
        image = self._get_image(x, y, extension)
        
        # Set dimensions
        self.input_height, self.input_width = image.height, image.width
        self.output_height, self.output_width = self.input_height, self.input_width
        if self.fov_x is not None:
            self.crop_width = restricted_fov(self.output_width, self.orig_fov_x, self.fov_x)
            self.crop_left = floor((self.output_width-self.crop_width)/2)
            self.output_width = self.crop_width
        else:
            self.crop_left = 0
            self.crop_width = self.output_width
            self.fov_x = self.orig_fov_x
        
        if self.fov_y is not None:
            self.crop_height = restricted_fov(self.output_height, self.orig_fov_y, self.fov_y)
            self.crop_top = floor((self.output_height-self.crop_height)/2)
            self.output_height = self.crop_height
        else:
            self.crop_top = 0
            self.crop_height = self.output_height
            self.fov_y = self.orig_fov_y

        self.output_height, self.output_width = round(self.ratio*self.output_height), round(self.ratio*self.output_width)

        self.buffer_height = (self.max_y+1)*self.output_height
        self.buffer_width = (self.max_x+1)*self.output_width

        return self._get_array(image)

    def set_shared_array_from_image(self, x, y, np_img, image):
        array_x_start = x*self.output_width
        array_y_start = (self.max_y-y)*self.output_height

        np_img[
            array_y_start:array_y_start+self.output_height,
            array_x_start:array_x_start+self.output_width,
            :
        ] = image

    
    def set_shared_array(self, x, y, extension, array):
        self.set_shared_array_from_image(
            x,
            y,
            np.ndarray((self.buffer_height, self.buffer_width, 3), dtype=np.uint8, buffer=array.buf),
            self._get_array(self._get_image(x, y, extension))
        )

