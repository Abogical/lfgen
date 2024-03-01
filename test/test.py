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

    def get_attrs_and_image(self, output_capture):
        output_image = None
        lf_attrs = None

        output_capture.buffer.seek(0)
        with ZipFile(output_capture.buffer) as zf:
            config_json = json.load(zf.open('config.json'))
            lf_attrs = config_json["lightFieldAttributes"]
            self.assertEqual(lf_attrs["hogelDimensions"], [self.width, self.height])
            self.assertEqual(lf_attrs["displayFOV"], [self.fov_x, self.fov_y])
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

    def test_downsampled_output(self):
        output_capture = io.TextIOWrapper(io.BytesIO())
        ratio = random.uniform(0.2, 0.9)

        with patch('sys.stdout', output_capture):
            with patch('sys.argv', ['lfgen', self.example_path, '-r', str(ratio)]):
                lfgen.main.main()

        lf_attrs, output_image = self.get_attrs_and_image(output_capture)

        height, width = round(self.height*ratio), round(self.width*ratio)
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


if __name__ == '__main__':
    unittest.main()