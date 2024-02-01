# Quilter

This is a script that returns a quilt suitable for light field images given a folder of images.
It supports downsampling the images before generating the quilt.

## Folder file structure
Each file in the folder needs to have the following filename format:
```
<x>-<y>.<image format>
```
Where:
- `x`: X value, or location from left edge
- `y`: Y value, or location from top edge
- `image format`: Any image format that OpenCV supports, or Nikon RAW format.

For example, the image at x-value 2 and y-value 7 may have a filename `2-7.NEF`.

## Usage
```
quilter [-h] [-r RATIO] [-o OUTPUT] directory
```
Where:
- `directory`: Source directory
- `-h`: Show help
- `-r RATIO` or ` --ratio RATIO`: Downsampling ratio to use
- `-o OUTPUT` or ` --output OUTPUT`: Output filename, default is standard output.

## Output

The output quilt image is a PNG file.