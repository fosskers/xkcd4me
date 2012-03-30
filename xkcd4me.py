#!/usr/bin/env python3

# file:    xkcd4me.py
# author:  Colin Woodbury
# contact: colingw AT gmail
# about:   Download and view all the xkcd comics you can handle!

# options:
#   n       Fetch the newest comic.
#   r       Fetch a random comic.
#   ###     Fetch comic ###.
#   xxx-yyy Fetch comics #xxx to #yyy.
#   all     Fetches all the comics. All of them.
#   ls      Lists all the comics you possess.
#   wipe    Clears the json file cache and all the comic files.

# Windows users: http://xkcd.com/272/
# Please get Cygwin: http://www.cygwin.com
# Or just: www.linuxmint.com
#          www.archlinux.org

# TODO: Rework how the script is activated.
#       Use traditional flags. 
#       The options listed above should be preceeded by a `-'.
#       -p or --prompt should bring up the prompt.
#       Simply running the script should equal `python xkcd4me.py n'.
#       Place a symlink in /usr/bin
#       Running the script for the first time should create a .conf file
#         with all the filepaths, etc., written it in.
#       During this, prompt the user for default image opener, etc?

from subprocess import getoutput as _getoutput
from random     import randrange as _randrange
from platform   import system    as _system
from json       import loads     as _loads
import httplib2
import sys
import os

## CONSTANTS
# Address of the latest comic's metadata.
BASE_URL    = 'http://xkcd.com/info.0.json'
# The working directory.
BASE_PATH   = os.getcwd()
# Directory for storing cached network requests.
CACHE_DIR   = BASE_PATH + '/.xkcd_cache'
# Diretory for storing the image files.
COMIC_DIR   = BASE_PATH + '/.comics'
# The user's Operating System.
USER_OS     = _system()
# The user's default way to open a picture file.
# If `None', tbe script will attempt to open it depending on OS.
OPEN_CMD    = 'feh'
# Text file containing mouseover text.
MO_TEXT     = '.mouseover-text.txt'
# Used for HTTP requests.
HTTP        = httplib2.Http(CACHE_DIR)
# An internet connection is available.
CONNECTED   = True
# The number of the most recent comic.
MOST_RECENT = 999999

## NON-CONSTANT GLOBALS
# A list of the current comics downloaded.
comic_list = None
# True if a new comic has been downloaded in the current session.
updated    = True

def check_dirs():
    '''Confirms if a .comics dir is present, and if it isn't, creates it.'''
    if not os.path.exists(COMIC_DIR):
        os.mkdir(COMIC_DIR)

def check_connection():
    '''Tests an internet connection. If it can connect, it records the 
    comic number of the most recent comic for later use.
    '''
    global CONNECTED, MOST_RECENT
    try:
        response, content = HTTP.request(BASE_URL)
        entry             = _loads(content.decode('utf-8'))
        MOST_RECENT       = entry['num']
    except httplib2.ServerNotFoundError:
        CONNECTED = False

def check_args():
    '''Checks args passed on the command line.'''
    if len(sys.argv) > 2:
        print('Bad args ->', sys.argv[1:])
        return  # Exits.
    exec_command(sys.argv[1])

def exec_command(choice):
    '''Executes a command given by the user.'''
    cmds = {'help': help, 'ls': print_comic_list, 'head': head,
            'tail': tail, 'wipe': wipe, 'r': random_comic, 'all': get_all,
            'q': done}
    if not choice or choice == 'n':
        get_comic_by_num(str(MOST_RECENT))  # Download the most recent comic.
    elif choice.isdigit():  
        get_comic_by_num(choice)
    elif valid_range(choice):
        get_comic_range(choice)
    elif choice in cmds:
        cmds[choice]()  # Execute their chosen command.
    else:
        print('{} is not a valid choice. '.format(choice), end='')
        print('Try again. You can do it.')

def prompt():
    '''Manages the script.'''
    print('Hi {}, welcome to xkcd4me!'.format(os.getlogin()))
    print('Type "help" to show a list of commands.')
    while True:
        choice = input('> ')
        exec_command(choice)

def help():
    '''Displays commands available in the prompt.'''
    cmds = ('n       -> Get the latest comic!',
            '###     -> Get comic number ###!',
            'xxx-yyy -> Get comics #xxx to #yyy!',
            'r       -> Get a random comic!',
            'ls      -> Show a list of all comics downloaded.',
            'head    -> Show your first ten comics.',
            'tail    -> Show your last ten comics.',
            'all     -> Get ALL the comics. (Be careful)',
            'wipe    -> Clears cache and comic archive.',
            'q       -> Get outta here!')
    for cmd in cmds:
        print(cmd)

def get_comic(url):
    '''Manages fetching the latest comic from the server.'''
    os.chdir(BASE_PATH)
    if CONNECTED:
        filename = dl_comic(url)
        open_image(filename)
    else:
        print('Server not found / No internet connection.')

def dl_comic(url):
    '''Downloads the comic file.'''
    global updated
    os.chdir(BASE_PATH)
    response, content = HTTP.request(url)
    entry             = _loads(content.decode('utf-8'))
    image_data        = get_image(entry['img'])
    filename          = get_filename(entry['title'], entry['num'])
    if image_data:
        os.chdir(COMIC_DIR)
        save_mouseover(entry['alt'], filename)
        write_image(image_data, filename)
        updated = True  # List displaying functions need this.
    return filename

def get_image(image_url):
    '''Via the metadata grabbed from the server, downloads the image.'''
    response, content = HTTP.request(image_url)
    if response.fromcache:
        content = None
    return content
    
def get_filename(title, num):
    '''Creates a valid filename given the title of the comic.'''
    bads  = ('(', ')', '/', ' ')
    title = ''.join(filter(lambda c: c not in bads, title))
    return ''.join(('{:04}-', title, '.png')).format(num)

def save_mouseover(text, filename):
    '''Saves the mouseover text.'''
    with open(MO_TEXT, 'a', encoding='utf-8') as tfile:
        tfile.write(filename + '|' + text + '\n')

def write_image(image_data, filename):
    '''Writes the downloaded image to an openable image.'''
    with open(filename, 'wb') as out_file:
        out_file.write(image_data)
    
def open_image(filename):
    '''Opens the image for viewing. Revamped 05/23/2011
    Linux users, please be wary of your window manager!
        'Linux': 'kde-open {}'  # For KDE window manager.
        'Linux': 'xdg-open {}'  # Window-manager-neutral.
    '''
    def display_image(line):
        '''Opens the file and shows mouseover text.'''
        print('Comic #{}!'.format(int(filename.split('-')[0])))
        show_mouseover(filename)
        os.system(line)
    # Move to the comic dir.
    os.chdir(COMIC_DIR)
    # Will open the image via a user indicated command,
    # or by detecting the OS and then opening it in a default way.
    os_cmds = {'Darwin': 'open {}', 'Linux': 'gnome-open {}',
               'Windows': 'cmd /c "start {}"'}
    if OPEN_CMD:
        display_image('{} {}'.format(OPEN_CMD, filename))
    elif USER_OS in os_cmds:
        display_image(os_cmds[USER_OS].format(filename))
    else:
        print('And just what operating system are you using?')
        print('Please set the OPEN_CMD variable to your default image viewer.')
        print('Or just go ahead and open the .png manually in .comics')

def show_mouseover(filename):
    '''Finds and displays the mouseover text.'''
    line = _getoutput('grep {} {}'.format(filename, MO_TEXT))
    text = line.split('|')
    if len(text) > 1:
        print('Mouseover text:', text[1])

def get_comic_by_num(choice):
    '''Shows the chosen comic. Downloads if necessary.'''
    filename = comic_search(choice)
    if int(choice) > MOST_RECENT or int(choice) in (0, 404):
        print('That comic does not exist!')
    elif filename:
        open_image(filename)
    else:
        print('Not in archive. Downloading fresh...')
        get_comic('http://xkcd.com/' + choice + '/info.0.json')

def comic_search(num):
    '''Checks .comics for the comic requested.'''
    comics = get_comic_list()
    for comic in comics:
        if '{:04}'.format(int(num)) == comic.split('-')[0]:
            return comic

def get_comic_list():
    '''Gets a list of all the archived comics from .comics'''
    global comic_list, updated
    if updated:
        os.chdir(COMIC_DIR)
        comic_list = os.listdir()
        comic_list.remove(MO_TEXT)  # Remove .mouseover-text.txt from the list.
        comic_list.sort()           # Linux ls does not auto-sort!
        updated = False
    return comic_list

def valid_range(choice):
    '''Checks if a given arg was a proper comic range.'''
    items = choice.split('-')
    if (len(items) == 2 and items[0].isdigit() and items[1].isdigit() and
        int(items[0]) < int(items[1]) and int(items[1]) <= MOST_RECENT):
            return True
    return False
        
def get_comic_range(choice):
    '''Downloads a range of comics.'''
    from time import time
    global updated
    items  = choice.split('-')
    bottom = int(items[0])
    top    = int(items[1])
    count  = 0
    print('Attempting download of comics {} through {}...'.format(bottom, top))
    if CONNECTED:
        start = time()
        for num in range(bottom, top+1):
            if num in (0, 404):  # 404 Error? Get it? Ha...
                continue
            if not comic_search(num):
                dl_comic('http://xkcd.com/' + str(num) + '/info.0.json')
                print('Downloaded comic {}.'.format(num))
                count += 1
        end = time()
        print('Downloaded {} new comics in {:.4} s.'.format(count, end - start))
        updated = True
    else:
        print('Server not found / No internet access.')
        
def random_comic():
    '''Opens a random comic.
    Without internet, it cycles only through the comics the user already has.
    '''
    if CONNECTED:        
        num = _randrange(1, int(MOST_RECENT))
        get_comic_by_num(str(num))
    else:
        comics = get_comic_list()
        if len(comics) > 0:
            num = _randrange(0, len(comics))
            open_image(comics[num])
        else:
            print('You don\'t have any comics on you,', end=' ')
            print('nor are you connected to the internet...')

def get_all():
    '''Downloads all the comics the user doesn't have.'''
    if sure():
        get_comic_range('1-{}'.format(MOST_RECENT))

def print_comic_list():
    '''Prints a list of all the comics downloaded by the user.'''
    comics = get_comic_list()
    print_items(comics)

def print_items(items):
    '''Prints all items in a given iterable.'''
    for item in items:
        print(item)

def head():
    '''Lists the first 10 comics.'''
    print_items(get_comic_list()[:10])

def tail():
    '''Lists the last 10 comics.'''
    print_items(get_comic_list()[-10:])

def wipe():
    '''Deletes all files in both .comics and .xkcd_cache.'''
    global comic_list
    print('This will delete all cache and comic files.')
    if sure():
        print('Clearing cache and comic archive...')
        clear_all_files(COMIC_DIR)
        wipe_cache()
        comic_list = None
        print('Done.')

def wipe_cache():
    '''Clears all the files in the cache.'''
    clear_all_files(CACHE_DIR)

def clear_all_files(path):
    os.chdir(path)
    files = os.listdir()
    for f in files:
        os.remove(f)

def sure():
    '''Asks if the user is sure. Really sure.'''
    print('Are you sure? (yes / no)')
    return input('> ') in ('y', 'yes')

def done():
    '''Quit.'''
    wipe_cache()
    quit()

if __name__ == '__main__':
    check_dirs()
    check_connection()
    if len(sys.argv) > 1:
        check_args()  # Command-line badassery.
    else:
        prompt()  # Helper prompt.
    done()
