'''
Copyright (C) 2024  Abdelrahman Abdelrahman

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
'''


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
from .image_processor import ImageProcessor
import concurrent.futures
import multiprocessing
import multiprocessing.managers
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

argument_parser.add_argument(
    '--fov-x',
    type=float,
    help='Simulate a restricted horizontal field of view'
)

argument_parser.add_argument(
    '--fov-y',
    type=float,
    help='Simulate a restricted vertical field of view'
)

argument_parser.add_argument(
    '-j', '--jobs',
    type=int,
    help='Number of jobs',
    default=multiprocessing.cpu_count()
)

argument_parser.add_argument(
    '--flip-y',
    help='Flip images vertically',
    action='store_true'
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
        else: 
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

    img_processor = ImageProcessor(
        arguments.directory,
        arguments.ratio,
        max_x,
        max_y,
        extra_config["displayFOV"][0],
        extra_config["displayFOV"][1],
        arguments.fov_x,
        arguments.fov_y,
        arguments.flip_y
    )
    
    total_images = (max_x+1)*(max_y+1)
    progress = tqdm(desc='Processing images', total=total_images)
    shared_array = None
    shared_np_array = None

    with multiprocessing.managers.SharedMemoryManager() as smm:
        with concurrent.futures.ProcessPoolExecutor(
            min(arguments.jobs, total_images-1),
            mp_context=multiprocessing.get_context('spawn')
        ) as pool:
            future_to_coord = {}
            for x in range(max_x+1):
                for y in range(max_y+1):
                    # progress.set_postfix_str(f'Current: ({x}, {y})')
                    extension = extension_grid[x].get(y)
                    if extension is None:
                        warnings.warn(f'Missing file for x:{x} and y:{y}. Will be blank in output image')
                    else:
                        if shared_array is None:
                            subimage = img_processor.set_dims_and_get_array(x, y, extension)
                            shared_array = smm.SharedMemory(
                                (max_x+1)*img_processor.output_width*(max_y+1)*img_processor.output_height*3
                            )
                            shared_np_array = img_processor.get_shared_numpy_array(shared_array)

                            img_processor.set_shared_array_from_image(x, y, shared_np_array, subimage)

                            extra_config["displayFOV"] = [img_processor.fov_x, img_processor.fov_y]
                            progress.set_postfix_str(f'Completed: ({x}, {y})')
                            progress.update(1)
                        else:
                            future_to_coord[pool.submit(img_processor.set_shared_array, x, y, extension, shared_array)] = (x,y)
            
            for future in concurrent.futures.as_completed(future_to_coord):
                x, y = future_to_coord[future]
                future.result() # Raise any errors if the process raised any
                progress.set_postfix_str(f'Completed: ({x}, {y})')
                progress.update(1)

        output = Image.new_from_array(shared_np_array)
        output_buffer = arguments.output or sys.stdout.buffer
        with ZipFile(output_buffer, mode='w') as zf:
            zf.writestr('config.json', json.dumps({
                "lightFieldAttributes": {
                    "hogelDimensions": [max_x+1, max_y+1],
                    "directionalResolution": [img_processor.output_width, img_processor.output_height],
                    "file": "image.png",
                    **extra_config
                }
            }))
            zf.writestr('image.png', output.pngsave_buffer())


if __name__ == "__main__":
    main()
