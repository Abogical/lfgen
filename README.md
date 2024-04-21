# lfgen

This is a script that returns an integral image suitable for light field images given a folder of images.
It supports downsampling the images before generating the integral image.

## Folder file structure
Each file in the folder needs to have the following filename format:
```
<x>-<y>.<image format>
```
Where:
- `x`: X value, or location from left edge
- `y`: Y value, or location from top edge
- `image format`: Any image format that `pillow` supports, or Nikon RAW format (NEF).

For example, the image at x-value 2 and y-value 7 may have a filename `2-7.png`.

## Usage
```
usage: lfgen [-h] [-r RATIO] [-o OUTPUT] [--fov-x FOV_X] [--fov-y FOV_Y] [-j JOBS] [--flip-y] directory

Generates a light field integral image from a folder of images

positional arguments:
  directory             Source directory

options:
  -h, --help            show this help message and exit
  -r RATIO, --ratio RATIO
                        Downsampling ratio to use
  -o OUTPUT, --output OUTPUT
                        Output filename, default is stdout
  --fov-x FOV_X         Simulate a restricted horizontal field of view
  --fov-y FOV_Y         Simulate a restricted vertical field of view
  -j JOBS, --jobs JOBS  Number of jobs
  --flip-y              Flip images vertically
```

## Output

The output integral image is an LF file with the config file and image inside it.

## Example image
The following is a 4x4 integral image downscaled down to 10% and cropped to 45 degrees in each dimension

![stitched](https://github.com/Abogical/lfgen/assets/10688496/0cb0f5af-c169-45db-8809-f47e5d630471)

Using this command
```
python -m lfgen.main --fov-x 45 --fov-y 45 -r 0.1 -o output.lf
```
