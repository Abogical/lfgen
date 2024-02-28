import argparse
import os
import re
import warnings
import sys
from collections import defaultdict
from PIL import Image
import numpy as np
from zipfile import ZipFile
import json
import rawpy
from concurrent import futures

argument_parser = argparse.ArgumentParser(
    prog='lfgen',
    description='Generates a light field integral image from a folder of images',
)

argument_parser.add_argument(
    'directory',
    type=str,
    help='Source directory'
)

argument_parser.add_argument(
    '-r', '--ratio',
    type=float,
    help='Downsampling ratio to use',
    default=1
)

argument_parser.add_argument(
    '-o', '--output',
    type=argparse.FileType(mode='wb'),
    help='Output filename, default is stdout',
)

argument_parser.add_argument(
    '-j', '--jobs',
    type=int,
    help='Number of jobs',
    default=8
)

filename_re = re.compile("(\\d+)-(\\d+)\\.(.*)")

class ImageProcessor:
    def __init__(self, ratio):
        self.ratio = ratio
        self.input_height = None
        self.input_width = None
        self.output_width = None
        self.output_height = None

    def _get_image_object(self, filename, extension):
        return (
            Image.fromarray(rawpy.imread(filename).postprocess())
            if extension.lower() == "nef" else
            Image.open(filename)
        )

    def _get_array_from_image(self, image):
        return np.array(image.resize((self.output_width, self.output_height)))

    def set_dims_and_get_array(self, filename, extension):
        with self._get_image_object(filename, extension) as image:
            self.input_height, self.input_width = image.height, image.width
            self.output_height, self.output_width = round(self.ratio*self.input_height), round(self.ratio*self.input_width)
            return self._get_array_from_image(image)

    def get_array(self, filename, extension):
        with self._get_image_object(filename, extension) as image:
            return self._get_array_from_image(image)

def set_suboutput(output, x, y, max_x, max_y, suboutput):
    output[
        (max_y-y)*suboutput.shape[0]:(max_y-y+1)*suboutput.shape[0],
        x*suboutput.shape[1]:(x+1)*suboutput.shape[1],
        :
    ] = suboutput


def main():
    arguments = argument_parser.parse_args()
    
    # Determine maximum x and y to set output resolution
    max_x, max_y = -1, -1
    extension_grid = defaultdict(dict)
    for filename in os.listdir(arguments.directory):
        match = filename_re.match(filename)
        if match is None:
            warnings.warn(f'Filename {filename} does not match lfgen format. Ignoring.', RuntimeWarning)
        else:
            x, y, ext = int(match.group(1)), int(match.group(2)), match.group(3)
            max_x = max(max_x, int(x))
            max_y = max(max_y, int(y))
            extension_grid[x][y] = ext

    if max_x == -1:
        # No filename found with a matching format
        raise SystemExit(f"No filename that matches the lfgen format is inside the directory {arguments.directory}")
    
    output = None
    image_processor = ImageProcessor(arguments.ratio)
    with futures.ThreadPoolExecutor(max_workers=arguments.jobs) as executor:
        future_to_coord = {}
        for x in range(max_x+1):
            for y in range(max_y+1):
                extension = extension_grid[x].get(y)
                if extension is None:
                    warnings.warn(f'Missing file for x:{x} and y:{y}. Will be blank in output image')
                else:
                    filename = os.path.join(arguments.directory, f'{x}-{y}.{extension}')
                    if output is None:
                        suboutput = image_processor.set_dims_and_get_array(filename, extension)
                        output = np.zeros(((max_y+1)*suboutput.shape[0], (max_x+1)*suboutput.shape[1], 3), dtype='uint8')
                        set_suboutput(output, x, y, max_x, max_y, suboutput)
                    else:
                        future_to_coord[executor.submit(image_processor.get_array, filename, extension)] = (x,y)
        
        for future in futures.as_completed(future_to_coord.keys()):
            x, y = future_to_coord[future]
            set_suboutput(output, x, y, max_x, max_y, future.result())

    output_buffer = arguments.output or sys.stdout.buffer
    with ZipFile(output_buffer, mode='w') as zf:
        zf.writestr('config.json', json.dumps({
            "lightFieldAttributes": {
                "hogelDimensions": [image_processor.input_width, image_processor.input_height],
                "file": "image.png"
            }
        }))
        with zf.open("image.png", mode='w') as image_zf:
            Image.fromarray(output).save(image_zf, format='png')


if __name__ == "__main__":
    main()
