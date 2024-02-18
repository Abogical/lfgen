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
lfgen [-h] [-r RATIO] [-o OUTPUT] directory
```
Where:
- `directory`: Source directory
- `-h`: Show help
- `-r RATIO` or ` --ratio RATIO`: Downsampling ratio to use
- `-o OUTPUT` or ` --output OUTPUT`: Output filename, default is standard output.

## Output

The output integral image is an LF file with the config file and image inside it.