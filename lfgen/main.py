import argparse
import os
import re
import warnings
import sys
from collections import defaultdict
import numpy as np
from zipfile import ZipFile
import json
from wand.image import Image

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

filename_re = re.compile("(\\d+)-(\\d+)\\.(.*)")

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

    output, input_height, input_width, output_height, output_width = None, None, None, None, None
    for x in range(max_x+1):
        for y in range(max_y+1):
            extension = extension_grid[x].get(y)
            if extension is None:
                warnings.warn(f'Missing file for x:{x} and y:{y}. Will be blank in output image')
            else:
                filename = f'{x}-{y}.{extension}'
                with Image(filename=os.path.join(arguments.directory, filename)) as image:
                    if output is None:
                        input_height, input_width = image.height, image.width
                        output_height, output_width = round(arguments.ratio*input_height), round(arguments.ratio*input_width)
                        output = np.zeros(((max_y+1)*output_height, (max_x+1)*output_width, 3), dtype='uint8')
                    elif (input_height, input_width) != (image.height, image.width):
                        warnings.warn(
                            f'Inconsistent input image resolutions. '
                            f'Expected {input_height}x{input_width}, '
                            f'got {image.height}x{image.width}.'
                        )
                    
                    # Downsample image and add image to integral image
                    if output_height != input_height or output_width != input_width:
                        image.resize(output_width, output_height, filter='gaussian')
                    
                    output[
                        y*output_height:(y+1)*output_height,
                        x*output_width:(x+1)*output_width,
                        :
                    ] = np.array(image)
    

    output_buffer = arguments.output or sys.stdout.buffer
    with ZipFile(output_buffer, mode='w') as zf:
        zf.writestr('config.json', json.dumps({
            "lightFieldAttributes": {
                "hogelDimensions": [input_width, input_height],
                "file": "image.png"
            }
        }))
        with zf.open("image.png", mode='w') as image_zf:
            image = Image.from_array(output)
            image.format = 'png'
            image.save(file=image_zf)


if __name__ == "__main__":
    main()