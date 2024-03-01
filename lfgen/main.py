import argparse
import os
import re
import warnings
import sys
from collections import defaultdict
from pyvips import Image
from zipfile import ZipFile
import json
import rawpy
from tqdm import tqdm
import itertools

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
    extra_config = {}
    for filename in os.listdir(arguments.directory):
        if filename == 'config.json':
            with open(os.path.join(arguments.directory, filename)) as config_file:
                extra_config = json.load(config_file)
            
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
    progress = tqdm(desc='Processing images', total=(max_x+1)*(max_y+1))
    for x in range(max_x+1):
        for y in range(max_y+1):
            progress.set_postfix_str(f'Current: ({x}, {y})')
            extension = extension_grid[x].get(y)
            if extension is None:
                warnings.warn(f'Missing file for x:{x} and y:{y}. Will be blank in output image')
            else:
                filename = os.path.join(arguments.directory, f'{x}-{y}.{extension}')
                image = None
                if extension.lower() == "nef":
                    with rawpy.imread(filename) as raw:
                        image = Image.new_from_array(raw.postprocess())
                else:
                    image = Image.new_from_file(filename)

                if output is None:
                    input_height, input_width = image.height, image.width
                    output_height, output_width = round(arguments.ratio*input_height), round(arguments.ratio*input_width)
                    output = Image.black((max_x+1)*output_width, (max_y+1)*output_height, bands=3)
                elif (input_height, input_width) != (image.height, image.width):
                    warnings.warn(
                        f'Inconsistent input image resolutions. '
                        f'Expected {input_height}x{input_width}, '
                        f'got {image.height}x{image.width}.'
                    )
                
                # Downsample image and add image to integral image
                if arguments.ratio != 1:
                    image = image.resize(
                        output_width/image.width,
                        vscale=output_height/image.height
                    )

                output = output.insert(
                    image,
                    x*output_width,
                    (max_y-y)*output_height,
                    expand=False
                )
            progress.update(1)
    

    output_buffer = arguments.output or sys.stdout.buffer
    with ZipFile(output_buffer, mode='w') as zf:
        zf.writestr('config.json', json.dumps({
            "lightFieldAttributes": {
                "hogelDimensions": [input_width, input_height],
                "file": "image.png",
                **extra_config
            }
        }))
        with zf.open("image.png", mode='w') as image_zf:
            image_zf.write(output.pngsave_buffer())


if __name__ == "__main__":
    main()
