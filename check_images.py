#TODO: how to do optional arguments?

import os, sys
import Image
import shutil
from directory_walker import DirectoryWalker

def check_image_sizes(images_dir, w, h, out_dir=''):
    '''
    Checks all the images inside images_dir, and compares their dimensions
    to width and height.

    If an image is found whose dimensions do not match width or height, 
    it will be moved to the directory out_dir.
    '''
    width = int(w)
    height = int(h)
    
    print 'Checking %s...' % images_dir
    dw = DirectoryWalker(images_dir)

    for filename in dw:
        file = filename
        try:
            print filename, 
            image = Image.open(file)
            size = image.size
            print size,

            if size[0] != width or size[1] != height:
                print '*',
                image = None
                if out_dir:
                    print 'moving...'
                    shutil.move(file, out_dir)
            print ''
        except IOError:
            print 'Error opening image. ' 
if __name__ == '__main__':
    src_dir = sys.argv[1]
    width = sys.argv[2]
    height = sys.argv[3]
    out_dir = sys.argv[4] 

    check_image_sizes(src_dir, width, height, out_dir) 

