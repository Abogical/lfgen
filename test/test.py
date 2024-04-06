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


import unittest
from unittest.mock import patch
import lfgen.main
import os
import shutil
import datetime
import random
from pyvips import Image
from pyvips.enums import BandFormat
from zipfile import ZipFile
import json
import io
from math import tan, radians, floor

class CLITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.example_path = os.path.join('test', '.artifacts', 'random_inputs', datetime.datetime.now().isoformat())
        cls.max_x = random.randint(1, 10)
        cls.max_y = random.randint(1, 10)
        
        cls.height = random.randint(200, 800)
        cls.width = random.randint(200, 800)
        cls.fov_x = random.uniform(90, 120)
        cls.fov_y = random.uniform(90, 120)

        os.makedirs(cls.example_path, exist_ok=True)
        for x in range(cls.max_x+1):
            for y in range(cls.max_y+1):
                Image.gaussnoise(cls.width, cls.height).bandjoin([
                    Image.gaussnoise(cls.width, cls.height),
                    Image.gaussnoise(cls.width, cls.height)
                ]).cast(BandFormat.UCHAR).pngsave(os.path.join(cls.example_path, f'{x}-{y}.png'))
        
        with open(os.path.join(cls.example_path, 'config.json'), 'w') as config_file:
            json.dump({
                "displayFOV": [cls.fov_x, cls.fov_y]
            }, config_file)

    @classmethod
    def tearDownClass(cls):
        try:
            shutil.rmtree(cls.example_path)
        except FileNotFoundError:
            pass

    def test_empty(self):
        with self.assertRaises(SystemExit):
            lfgen.main.main()

    @patch("sys.argv", ['lfgen', os.path.join('test', 'gibberish')])
    def test_non_existent_directory(self):
        with self.assertRaises(FileNotFoundError):
            lfgen.main.main()

    def get_attrs_and_image(self, output_capture, output_width=None, output_height=None, fov_x=None, fov_y=None):
        output_image = None
        lf_attrs = None
        fov_x = fov_x or self.fov_x
        fov_y = fov_y or self.fov_y
        output_width = output_width or self.width
        output_height = output_height or self.height

        output_capture.buffer.seek(0)
        with ZipFile(output_capture.buffer) as zf:
            config_json = json.load(zf.open('config.json'))
            lf_attrs = config_json["lightFieldAttributes"]
            self.assertEqual(lf_attrs["hogelDimensions"], [self.max_x+1, self.max_y+1])
            self.assertEqual(lf_attrs["directionalResolution"], [output_width, output_height])
            self.assertEqual(lf_attrs["displayFOV"], [fov_x, fov_y])
            with zf.open(lf_attrs["file"]) as img_file:
                output_image = Image.pngload_buffer(img_file.read())

        return lf_attrs, output_image        

    def test_lossless_output(self):
        output_capture = io.TextIOWrapper(io.BytesIO())

        with patch('sys.stdout', output_capture):
            with patch('sys.argv', ['lfgen', self.example_path]):
                lfgen.main.main()

        lf_attrs, output_image = self.get_attrs_and_image(output_capture)

        for x in range(self.max_x+1):
            for y in range(self.max_y+1):
                im = Image.new_from_file(os.path.join(self.example_path, f'{x}-{y}.png'))
                self.assertEqual(
                    (im == output_image.crop(x*self.width, (self.max_y-y)*self.height, self.width, self.height)).min(),
                    255
                )

    def test_flipped_output(self):
        output_capture = io.TextIOWrapper(io.BytesIO())

        with patch('sys.stdout', output_capture):
            with patch('sys.argv', ['lfgen', '--flip-y', self.example_path]):
                lfgen.main.main()

        lf_attrs, output_image = self.get_attrs_and_image(output_capture)

        for x in range(self.max_x+1):
            for y in range(self.max_y+1):
                im = Image.new_from_file(os.path.join(self.example_path, f'{x}-{y}.png'))
                self.assertEqual(
                    (im == output_image.crop(x*self.width, (self.max_y-y)*self.height, self.width, self.height).flipver()).min(),
                    255
                )

    def test_downsampled_output(self):
        output_capture = io.TextIOWrapper(io.BytesIO())
        ratio = random.uniform(0.2, 0.9)

        with patch('sys.stdout', output_capture):
            with patch('sys.argv', ['lfgen', self.example_path, '-r', str(ratio)]):
                lfgen.main.main()

        height, width = round(self.height*ratio), round(self.width*ratio)
        lf_attrs, output_image = self.get_attrs_and_image(output_capture, width, height)

        for x in range(self.max_x+1):
            for y in range(self.max_y+1):
                im = Image.new_from_file(os.path.join(self.example_path, f'{x}-{y}.png')).resize(
                    width/self.width,
                    vscale=height/self.height
                )
                self.assertEqual(
                    (im == output_image.crop(x*width, (self.max_y-y)*height, width, height)).min(),
                    255
                )

    def test_limited_fov_output(self):
        output_capture = io.TextIOWrapper(io.BytesIO())
        ratio = random.uniform(0.2, 0.9)
        output_fov_x = random.uniform(45, self.fov_x)
        output_fov_y = random.uniform(45, self.fov_y)

        with patch('sys.stdout', output_capture):
            with patch('sys.argv', ['lfgen', self.example_path, '-r', str(ratio),
                '--fov-x', str(output_fov_x), '--fov-y', str(output_fov_y)]):
                lfgen.main.main()

        calculate_dim = lambda a, fov, new_fov: round(a*
            tan(radians(new_fov/2))/tan(radians(fov/2)))
        crop_height, crop_width = (
            calculate_dim(self.height, self.fov_y, output_fov_y),
            calculate_dim(self.width, self.fov_x, output_fov_x)
        )
        height, width = (
            round(crop_height*ratio),
            round(crop_width*ratio)
        )

        lf_attrs, output_image = self.get_attrs_and_image(output_capture, width, height, output_fov_x, output_fov_y)
        
        for x in range(self.max_x+1):
            for y in range(self.max_y+1):
                im = Image.new_from_file(os.path.join(self.example_path, f'{x}-{y}.png'))
                im = im.crop(
                    floor((im.width-crop_width)/2),
                    floor((im.height-crop_height)/2),
                    crop_width,
                    crop_height
                )
                im = im.resize(
                    width/im.width,
                    vscale=height/im.height
                )
                self.assertEqual(
                    (im == output_image.crop(x*width, (self.max_y-y)*height, width, height)).min(),
                    255
                )


if __name__ == '__main__':
    unittest.main()
