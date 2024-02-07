import argparse
import os
import re
import warnings
import sys
from collections import defaultdict
import cv2
import numpy as np

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
    filename_grid = defaultdict(dict)
    for filename in os.listdir(arguments.directory):
        match = filename_re.match(filename)
        if match is None:
            warnings.warn(f'Filename {filename} does not match lfgen format. Ignoring.', RuntimeWarning)
        else:
            x, y = int(match.group(1)), int(match.group(2))
            max_x = max(max_x, int(x))
            max_y = max(max_y, int(y))
            filename_grid[x][y] = filename

    if max_x == -1:
        # No filename found with a matching format
        raise SystemExit(f"No filename that matches the lfgen format is inside the directory {arguments.directory}")

    output, input_height, input_width, output_height, output_width = None, None, None, None, None
    for x in range(max_x+1):
        for y in range(max_y+1):
            filename = filename_grid[x].get(y)
            if filename is None:
                warnings.warn(f'Missing file for x:{x} and y:{y}. Will be blank in output image')
            else:
                image = cv2.imread(os.path.join(arguments.directory, filename))
                if output is None:
                    input_height, input_width = image.shape[0:2]
                    output_height, output_width = round(arguments.ratio*input_height), round(arguments.ratio*input_width)
                    output = np.zeros(((max_y+1)*output_height, (max_x+1)*output_width, 3))
                elif (input_height, input_width) != image.shape[0:2]:
                    warnings.warn(
                        f'Inconsistent input image resolutions. '
                        f'Expected {input_height}x{input_width}, '
                        f'got {image.shape[0]}x{image.shape[1]}.'
                    )
                # Downsample image
                image = cv2.resize(image, (output_width, output_height))
                # Add image to integral image
                output[y*output_height:(y+1)*output_height, x*output_width:(x+1)*output_width, :] = image
    
    _, buffer = cv2.imencode(".png", output)
    output_buffer = arguments.output or sys.stdout.buffer
    output_buffer.write(buffer)


if __name__ == "__main__":
    main()