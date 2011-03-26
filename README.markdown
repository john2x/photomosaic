# Requirements
- [Python Imaging Library][PIL]

# Usage
## Prepare your image pool
1. Collect a ton of images (2000 is a good number) for your image pool and place them in a directory (e.g. `tiles/`). Make sure they are the same size and w/h ratio\*.
2. Run `$ python create_image_pool.py tiles/` to create the tiles database.

\* use `check_images.py` to "weed" out images with different ratios 
    `$ python check_images.py tiles_dir desired_width desired_height weeded_tiles_dir`
This will put all images not matching `desired_width` and `desired_height` into `weeded_tiles_dir` so you can fix them later on and re-add them into the image pool.  

## Creating the mosaic
After running `create_image_pool.py`, you can now create mosaics.
    $ python photomosaic.py [options] source_image.jpg output_image.jpg tiles_dir

### options
- `-p RATIO`: Ratio between the tile size and subdivisions of the image. Set to higher numbers for finer details. Use whole numbers only. e.g. A RATIO of 4 would place 4 tiles into 1 subdivision of the image. Default is 1.
- `-m METHOD, --method=METHOD`: Traversing method. (`inside-out` or `top-down`) Determines where to start traversing the source image. 
- `-r --repeat`: Allow repeating of tiles
- `-n --norepeat`: Do not allow repeating of tiles [default]
- `-t THRESHOLD, --threshold=THRESHOLD`: Threshold value for comparing colors. Default is 0.
- `-v --verbose`: Verbose output.
- `-x XSTART, --xStart=XSTART`: X position of where to start matching. For `inside-out` method only. 
- `-y YSTART, --yStart=YSTART`: Y position of where to start matching. For `inside-out` method only. 

* * *

Sample results and more info can be found on my [website][].

[PIL]: http://www.pythonware.com/products/pil/
[website]: http://john2x.com/projects/photomosaics
