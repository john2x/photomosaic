
import os, sys
import sqlite3
import Image
from directory_walker import DirectoryWalker

def create_image_pool(image_dir, sqlite_db='imagepool.db'):
    '''
    Creates a SQLite database named sqlite_db of all images in image_dir
    with fields
    'image', 'red', 'green', 'blue'
    where:
        image = filename of the image
        red = value of red in RGB of average color of image
        green = value of green in RGB
        blue = value of blue in RGB
    '''
    db = connect_database(os.path.join(image_dir, sqlite_db))
    cursor = db.cursor()

    dw = DirectoryWalker(image_dir) 
    #traverse through image_dir
    for file in dw:
        filename = os.path.split(file)[1]
        try:
            im = Image.open(file)
        except IOError:
            print 'Cannot open image file:', os.path.split(file)[1] 
            continue
        
        ave_colors = []
        subs = subdivide(im)
        for area in subs:
            ave_colors.append(average_rgb(area))
        ave_rgb = average_rgb(im)
        insert(filename, ave_rgb, ave_colors, db)

    cursor.execute('SELECT * FROM Images')
    for row in cursor:
        print row

    cursor.close()
    db.commit()
    print 'Success!'
            
def insert(image, rgb, colors, db):
    cursor = db.cursor()
    try:
        cursor.execute(
            '''INSERT INTO Images
                (image, used, red, green, blue)
                VALUES (?, ?, ?, ?, ?)''',
            (image, 0, rgb[0], rgb[1], rgb[2])
        )
        cursor.execute('SELECT id FROM Images WHERE image=?', (image, ))
        id = cursor.fetchone()[0]
        for pos, rgb in enumerate(colors):
            cursor.execute(
                '''INSERT INTO Colors
                    (image_id, pos, red, green, blue)
                    VALUES(?, ?, ?, ?, ?)''',
                (id, pos, rgb[0], rgb[1], rgb[2])
            )

    except sqlite3.IntegrityError, e:
        print 'Image %s already in table. ' % image

def connect_database(db):
    try:
        dbconn = sqlite3.connect(db)
        create_tables(dbconn)
    except IOError:
        print 'Cannot connect to database. '
        return 

    return dbconn

def create_tables(db):
    cursor = db.cursor()
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS Images
        (id INTEGER PRIMARY KEY,
        image TEXT UNIQUE,
        used INTEGER,
        red INTEGER,
        green INTEGER,
        blue INTEGER)'''
    )
    cursor.execute(
        '''CREATE TABLE IF NOT EXISTS Colors
        (id INTEGER PRIMARY KEY,
        image_id INTEGER,
        pos INTEGER,
        red INTEGER,
        green INTEGER,
        blue INTEGER)'''
    )
    cursor.close()
    db.commit()

def subdivide(image):
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

if __name__ == '__main__':
    create_image_pool(sys.argv[1])

