import unittest
from unittest.mock import patch
import quilter.main
import os
import shutil
import datetime
import random
import numpy as np
import cv2
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
                cv2.imwrite(os.path.join(cls.example_path, f'{x}-{y}.png'), random_image)

    @classmethod
    def tearDownClass(cls):
        try:
            shutil.rmtree(cls.example_path)
        except FileNotFoundError:
            pass

    def test_empty(self):
        with self.assertRaises(SystemExit):
            quilter.main.main()

    @patch("sys.argv", ['quilter', os.path.join('test', 'gibberish')])
    def test_non_existent_directory(self):
        with self.assertRaises(FileNotFoundError):
            quilter.main.main()

    def test_lossless_output(self):
        output_capture = io.TextIOWrapper(io.BytesIO())

        with patch('sys.stdout', output_capture):
            with patch('sys.argv', ['quilter', self.example_path]):
                quilter.main.main()

        output_image = cv2.imdecode(np.frombuffer(output_capture.buffer.getvalue(), np.uint8), 1)

        for x in range(self.max_x+1):
            for y in range(self.max_y+1):
                self.assertTrue((
                    cv2.imread(os.path.join(self.example_path, f'{x}-{y}.png')) ==
                    output_image[y*self.height:(y+1)*self.height, x*self.width:(x+1)*self.width, :]
                ).all())

    def test_downsampled_output(self):
        output_capture = io.TextIOWrapper(io.BytesIO())
        ratio = random.uniform(0.2, 0.9)

        with patch('sys.stdout', output_capture):
            with patch('sys.argv', ['quilter', self.example_path, '-r', str(ratio)]):
                quilter.main.main()

        output_image = cv2.imdecode(np.frombuffer(output_capture.buffer.getvalue(), np.uint8), 1)

        height, width = round(self.height*ratio), round(self.width*ratio)
        for x in range(self.max_x+1):
            for y in range(self.max_y+1):
                self.assertTrue((
                    cv2.resize(
                        cv2.imread(os.path.join(self.example_path, f'{x}-{y}.png')),
                        (width, height)
                    ) == output_image[y*height:(y+1)*height, x*width:(x+1)*width, :]
                ).all())


if __name__ == '__main__':
    unittest.main()