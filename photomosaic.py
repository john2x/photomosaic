#TODO: fix black artifacts
#TODO: optimize find_closest_match (better color matching)
#TODO: look into fractional ratios
#TODO: new repeat; allow repeats when out of images 
#TODO: new repeat; allow repeats at a specified distance

import os, sys
import sqlite3
import Image
import time
from math import sqrt
from optparse import OptionParser

INSIDE_OUT = 'inside-out'
TOP_DOWN = 'top-down'

def create_mosaic(source, output, pool_dir, 
                  ratio, method, repeat, threshold, verbose):
        '''
        source = source image; must be 4:3 or 3:4 ratio
        output = output filename
        image_pool_dir = directory of the tile image pool; 
                            must have imagepool.db inside
        ratio = ratio between output and source;
                e.g. ratio of 2 means output will be 2 times bigger than source
                the higher the ratio, the more detailed the output
        repeat = if tiles can be repeated or not
        threshold = threshold to use for acceptable difference between colors
        '''
        dir = os.path.split(source)[0]
        size_ratio = ratio
        imagepool = connect_database(os.path.join(pool_dir, 'imagepool.db'))
        cursor = imagepool.cursor()
        tile_size = get_tilesize(imagepool, pool_dir)
        #subdivide source image into tiles 
        try:
            source_image = Image.open(source)
        except IOError:
            print 'Cannot open source image %s' % source
            return
        subdivision_size = (tile_size[0] / size_ratio, tile_size[1] / size_ratio)
        source_grid = subdivide_source(source_image, subdivision_size)
        output_size = (len(source_grid[0]) * tile_size[0],
                       len(source_grid) * tile_size[1]) 
        mosaic = Image.new('RGB', output_size)
        
        width = source_image.size[0] / (tile_size[0] / size_ratio)
        height = source_image.size[1] / (tile_size[1] / size_ratio)
        print '%d x %d = %d' % (width, height, width * height)

        #Loop through tile_grid, then compare each tile from source_image with every 
        #tile in imagepool. Find the closest match, then place that tile in place.
        try:
            if method == TOP_DOWN:
                top_down(source_grid, mosaic, tile_size, pool_dir, imagepool, 
                         repeat, threshold, verbose)
            elif method == INSIDE_OUT:
                inside_out(source_grid, mosaic, tile_size, pool_dir, imagepool,
                           repeat, threshold, verbose)
            else:
                raise ValueError
        except KeyboardInterrupt:
            print 'Cancelled by user. '
            cursor.close()
            reset_imagepool(imagepool)
            return
        except ValueError:
            print '%s is not a valid method. ' % method
        else:
            output_image(mosaic, output)
            print 'Success! Generated %s from %s' % (output, source)
        finally:
            cursor.close()
            reset_imagepool(imagepool)

def top_down(grid, output, tile_size, pool_dir, db, repeat, threshold, verbose):
    '''
    Starts matching from top-left, going to bottom-right
    '''
    counter = 0
    for yPos, y in enumerate(grid):
        for xPos, x in enumerate(grid[yPos]):
            if verbose:
                print counter, 
            tile_name = find_closest_match(grid[yPos][xPos], 
                                           db, repeat,
                                          threshold, verbose)
            tile = Image.open(os.path.join(pool_dir, tile_name))
            output.paste(tile, (xPos * tile_size[0], yPos * tile_size[1]))
            counter += 1

def bottom_up(grid, output, tile_size, pool_dir, db, repeat):
    pass

def inside_out(grid, output, tile_size, pool_dir, db, repeat, threshold,
              verbose, start=None):
    '''
    Starts matching from the center of the grid, going outwards.
    '''
    map = [[0 for x in grid[0]] for y in grid]  #maps which tiles are already matched
    if not start:
        start_x = len(grid[0]) / 2
        start_y = len(grid) / 2
    else:
        start_x = start[0]
        start_y = start[1]
    end_x = start_x + 1
    end_y = start_y + 1
    counter = 0
    while 1:
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                if not map[y][x]:
                    if verbose:
                        print counter,
                    tile_name = find_closest_match(grid[y][x], 
                                                   db, repeat, 
                                                  threshold, verbose)
                    tile = Image.open(os.path.join(pool_dir, tile_name))
                    output.paste(tile, (x * tile_size[0], 
                                        y * tile_size[1]))
                    map[y][x] = 1
                    counter += 1
        start_x = start_x - 1 if start_x >= 0 else -1
        start_y = start_y - 1 if start_y >= 0 else -1
        end_x = end_x + 1 if end_x <= len(grid[0]) - 1 else len(grid[0]) 
        end_y = end_y + 1 if end_y <= len(grid) - 1 else len(grid)
        if start_x < 0 and start_y < 0 \
           and end_x > len(grid[0]) - 1 and end_y > len(grid) - 1:
            break

def find_closest_match(image, db, repeat, threshold, verbose):
    '''
    Find the closest match of image from the image pool.
    Returns an Image instance. 
    '''
    cursor = db.cursor()
    #subdivide image into tiles again
    subs = subdivide_tile(image)
    target_rgb = []
    diff_rgb = []
    diff_id = []
    total_diff_for_tile = 0
    #get average RGB vector from the 9 subdivisions of the tile
    for sub in subs:
        target_rgb.append(average_rgb(sub))

    #get all usable tile images from imagepool database
    if repeat:
        cursor.execute(
            '''SELECT id, image_id, red, green, blue, pos
            FROM Colors'''
        )
    else:
        cursor.execute(
            '''SELECT C.id, C.image_id, C.red, C.green, C.blue, C.pos
            FROM Colors C, Images I 
            WHERE C.image_id=I.id 
            AND used=0'''
        )
    #compare each sub-tile of subs to each average color in Colors table
    #calculate the difference
    #then get the total difference between the source tile and the
    #imagepool tile
    for row in cursor:
        pos = row[5]
        diff = difference((row[2], row[3], row[4]), (target_rgb[pos]))
        total_diff_for_tile += diff
        if pos == 8:
            diff_rgb.append(total_diff_for_tile)
            diff_id.append(row[1])
            if threshold and total_diff_for_tile < threshold:
                diff_rgb = [total_diff_for_tile, ]
                diff_id = [row[1], ]
            total_diff_for_tile = 0

    #find the imagepool tile with the least difference between source tile
    closest_rgb = min(diff_rgb)
    closest_id = diff_id[diff_rgb.index(closest_rgb)]
    if not repeat:
        cursor.execute(
            '''UPDATE Images SET used=1 WHERE id=?''', (closest_id, )
        )
        db.commit()
    cursor.execute(
        '''SELECT image FROM Images WHERE id=?''', (closest_id, )
    )
    closest_tile = cursor.fetchone()[0]
    if verbose:
        print closest_tile, closest_rgb
    return closest_tile
    
def difference(rgb1, rgb2):
    '''
    Returns the 3-tuple difference between rgb1 and rgb 2
    '''
    diff = sqrt((rgb1[0] - rgb2[0]) ** 2 + (rgb1[1] - rgb2[1]) ** 2 + 
    (rgb1[2] - rgb2[2]) ** 2)
    return diff

def subdivide_source(image, tile_size):
    '''
    Subdivides a large image into smaller tiles of size tile_size.
    Returns a 2-dimensional list of Image tiles. 
    '''
    width = image.size[0] / tile_size[0]
    height = image.size[1] / tile_size[1]
    grid = [[None for w in range(width)] for h in range(height)]
    for y in range(height):
        for x in range(width):
            cell = image.crop((x * tile_size[0], 
                               y * tile_size[1],
                               x * tile_size[0] + tile_size[0], 
                               y * tile_size[1] + tile_size[1]))
            grid[y][x] = cell       
    return grid

def subdivide_tile(image):
    '''
    Subdivide tile image into 3x3 sub tile.
    Used for subsampling.
    Returns a 3x3 grid of Image tiles.
    '''
    w = image.size[0] / 3
    h = image.size[1] / 3
    subdivisions = [] 

    for y in range(3):
        for x in range(3):
            cropped = image.crop((x * w, y * h, x * w + w, y * h + h))
            subdivisions.append(cropped)
    return subdivisions

def average_rgb(image):
    '''
    Calculates the average RGB of an image.
    Returns 3-tuple (R, G, B)
    '''
    average_red = 0
    average_green = 0
    average_blue = 0
    maxcolors = image.size[0]*image.size[1]
    colors = image.getcolors(maxcolors)
    for color in colors:
        average_red += color[1][0] * color[0]
        average_green += color[1][1] * color[0]
        average_blue += color[1][2] * color[0]
    average_red /= maxcolors
    average_green /= maxcolors
    average_blue /= maxcolors
    return (average_red, average_green, average_blue)

def connect_database(db):
    try:
        dbconn = sqlite3.connect(db)
    except IOError:
        print 'Cannot connect to database. '

    return dbconn

def reset_imagepool(db):
    try:
        cursor = db.cursor()
        cursor.execute(
            '''UPDATE Images SET used=0 WHERE used=1'''
        )
        db.commit()
    except sqlite3.OperationalError, e:
        print e

def output_grid(grid, size, tile_size):
    output = Image.new('RGB', size)
    print tile_size
    for yPos, y in enumerate(grid):
        for xPos, x in enumerate(grid[yPos]):
            output.paste(x, (xPos * tile_size[0] / 2, yPos * tile_size[1] / 2))

    output_image(output, 'grid.jpg')

def output_image(image, filename):
    try:
        image.save(os.path.join(os.getcwd(), filename))
    except IOError:
        print 'Cannot save image ', filename

def get_tilesize(db, pool_dir):
    cursor = db.cursor()
    cursor.execute('SELECT image FROM Images WHERE id=1')
    tilename = cursor.fetchone()[0]
    tile = Image.open(os.path.join(pool_dir,tilename))
    return tile.size

def main():
    usage = 'usage: %prog [options] source_image output_image tiles_directory'
    parser = OptionParser(usage)
    parser.add_option('-p',
                      dest='ratio', type='int', default=1,
          help='ratio between tile size and subdivisions of source image [default=1]')
    parser.add_option('-m', '--method', type='choice',
                      dest='method', default='inside-out',
                      choices=['inside-out', 'top-down'],
          help='traversing method (inside-out, top-down) [default=%default]')
    parser.add_option('-r', '--repeat',
                      dest='repeat',
                      action='store_true',
                      help='allow repeating tiles')
    parser.add_option('-n', '--norepeat',
                      dest='repeat',
                      action='store_false', default=False,
                      help='do not allow repeating tiles [default]')
    parser.add_option('-t', '--threshold',
                      dest='threshold', default=0, type='int',
                      help='''threshold value for comparing colors. 
                      0 for no threshold [default=0]''')
    parser.add_option('-x', '--xStart',
                      dest='xStart', default=None,
                      help='''X position of where to start matching. For inside-out
                      only''')
    parser.add_option('-y', '--yStart',
                      dest='yStart', default=None,
                      help='''Y position of where to start matching. For inside-out
                      only''')
    parser.add_option('-v', '--verbose',
                      dest='verbose',
                      action='store_true', default=False)
    (options, args) = parser.parse_args()
    if len(args) == 3:
        create_mosaic(args[0], args[1], args[2],
                      options.ratio, options.method, options.repeat,
                     options.threshold, options.verbose)
    else:
        parser.error('Incorrect number of arguments. ')
    parser.destroy()

if __name__ == '__main__':
    start_time = time.clock()
    main()
    print 'Completed in', time.clock() - start_time, 'seconds'
