import unittest
from unittest.mock import patch
import lfgen.main
import os
import shutil
import datetime
import random
import numpy as np
from PIL import Image
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

        os.makedirs(cls.example_path, exist_ok=True)
        for x in range(cls.max_x+1):
            for y in range(cls.max_y+1):
                random_image = np.random.randint(0, 256, (cls.height, cls.width, 3), dtype=np.uint8)
                Image.fromarray(random_image).save(os.path.join(cls.example_path, f'{x}-{y}.png'))

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
            with Image.open(zf.open(lf_attrs["file"]), formats=[os.path.splitext(lf_attrs["file"])[1][1:]]) as im:
                output_image = np.array(im)

        return lf_attrs, output_image        

    def test_lossless_output(self):
        output_capture = io.TextIOWrapper(io.BytesIO())

        with patch('sys.stdout', output_capture):
            with patch('sys.argv', ['lfgen', self.example_path]):
                lfgen.main.main()

        lf_attrs, output_image = self.get_attrs_and_image(output_capture)

        for x in range(self.max_x+1):
            for y in range(self.max_y+1):
                self.assertTrue((
                    np.array(Image.open(os.path.join(self.example_path, f'{x}-{y}.png'))) ==
                    output_image[y*self.height:(y+1)*self.height, x*self.width:(x+1)*self.width, :]
                ).all())

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
                with Image.open(os.path.join(self.example_path, f'{x}-{y}.png')) as im: 
                    self.assertTrue((
                        np.array(im.resize((width, height))) ==
                        output_image[y*height:(y+1)*height, x*width:(x+1)*width, :]
                    ).all())


if __name__ == '__main__':
    unittest.main()