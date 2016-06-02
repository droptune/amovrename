#! /usr/bin/env python
# amovrename.py
# Renames MOV files using MOV metadata modification time as name.
#

import os
import sys
import time
import re
import struct
import argparse
import glob


def print_help():
    print(
        "\n"
        "movrename.py [-h] [-e EXTENSION] [-f \"FORMAT\"] FILES\n"
        "\n"
        "-h, --help\t\t\t\tshow this help\n"
        "FILES - files or path to files to rename"
        "-a, --advanced\t\t\tadvanced mode with several renaming options"
        "-e EXTENSION, --extension EXTENSION\tuse specified extension (default = mov)\n"
        "-f FORMAT, --format FORMAT\t\taccepts standart time variables as specified at:\n"
        "\n"
        "\thttps://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior\n"
        "\n"
        "Default format is %Y%m%d-%H%M which results in files 20160120-1305.mov\n"
        "with additional index appended if file with the same name exists in folder.\n"
        )
    
    
def get_file_names(path, extension):
    """
    Gets filelist to process
    """
    worklist = []   # empty worklist of files
    filelist = []    # list for old names
    
    # Will be checking only files whith specified extensions
    extension_check = re.compile('(\.' + extension + ')$', re.I)
    
    # Populate work files list
    for filename in path:
        # Check for wildcards
        if re.search('\*|\?', filename):
            path.extend(glob.glob(filename))
            continue
    
        if os.path.isdir(filename):
            tempfiles = os.listdir(os.path.abspath(filename))
            for f in tempfiles:
                # skip subdirs
                if os.path.isdir(f):
                    continue
                worklist.append(os.path.join(os.path.abspath(filename), os.path.basename(f)))
        # Skip non-existent files
        elif os.path.isfile(filename):
            worklist.append(filename)
    
    for filename in worklist:
        if extension_check.search(filename):
            filelist.append(filename)
    
    return filelist


def get_new_filenames(files_times, use_time, extension):
    """
    Creates list of new filenames appending index when new name
    already exists
    """
    newnames = []
    extension_check = re.compile('(\.' + extension + ')$', re.I)
    
    for filename, filetime in files_times:
        extension = extension_check.search(filename).group(1)
        # Create new name
        t = filetime[use_time][1]
                
        if t == 0:
            # No creation time for this file found
            # Will try to use old name. Adding index if it overlaps
            # with new filenames
            newname = filename
        else:
            newname = t + extension
                       
        idx = 0
        newname_no_index = newname[:-4]
            
        # If new filename exists in newnames list append index to it
        while newname in newnames:
            idx += 1
            newname = newname_no_index + '-' + str(idx) + extension
        newnames.append(newname)
    
    return newnames


def get_file_times(files, time_format):
    """
    Gets list of system and QT times from files
    """
    times = []      # list of different times for files
    
    for filename in files:
        filetime = {'file': [0, 0]}  # Will contain all time values we will find
    
        # Get file mtime
        filetime['file'][1] = os.path.getmtime(filename)
        
        # Get moov times
        filetime.update(get_moov_time(filename))        
        
        # Format all times according to provided template
        try:
            format_time(filetime, time_format)
        except ValueError:
            print('Error in time format "{0}."'.format(time_format))
            sys.exit(1)
        
        times.append(filetime)
    
    return times


def format_time(times, time_format):
    """
    Formats times according to provided template
    """
    for item in times:
        for time_item in range(len(times[item])):
            times[item][time_item] = time.strftime(
                time_format,
                time.localtime(times[item][time_item])
            )


def read_times(filename):
    """
    Reads creation and modification time given the beginning of atom
    """
    QT_EPOCH = 2082844800
    filename.seek(4, 1)
    ctime = struct.unpack('>I', filename.read(4))[0] - QT_EPOCH
    mtime = struct.unpack('>I', filename.read(4))[0] - QT_EPOCH
    return [ctime, mtime]


def get_moov_time(filename):
    """
    Gets movie creation time from moov atom. Returns 0 in case of error.
    """
    # atom: header, length after dates
    mov_atoms = {b'moov': {'header': b'mvhd', 'size': 88}}
    moov_atoms = {b'trak': {'header': b'tkhd', 'size': 72},
                  b'mdia': {'header': b'mdhd', 'size': 12}}
    # moov ctime/mtime, trak ctime/mtime, mdia ctime/mtime
    times = {'moov': [0, 0], 'trak': [0, 0], 'mdia': [0, 0]}
    
    movie = open(filename, 'r+b')
    
    # atoms to search for
    atoms = mov_atoms
    # Read atoms in file until we find moov or reach the end
    # Then search for inner moov atoms
    while True:
        try:
            atom_size, atom_type = struct.unpack('>L4s', movie.read(8))
        except:
            break
        
        if atom_type in atoms:
            header = movie.read(8)[4:8]
            # Check for correct header and read times
            if header == atoms[atom_type]['header']:
                times[atom_type.decode()] = read_times(movie)
            
            # seek to the end of atom
            movie.seek(atoms[atom_type]['size'], 1)
        
        # If found moov continue to inner moov atoms
        if atom_type == b'moov':
            atoms = moov_atoms
        
        else:
            if atom_size < 8:
                break
            movie.seek(atom_size - 8, os.SEEK_CUR)

    movie.close()
    return times
            

def main(argv):
    """
    Main
    """
    
    name_format = "%Y%m%d-%H%M"  # Default name format
    extension = 'mov'            # Default extension
    use_time = 'moov'      # By default use quicktime metadata time

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Get arguments.', add_help=False)
    parser.add_argument('filename', nargs='*')
    parser.add_argument('--format', '-f',
                        help='provide file format')
    parser.add_argument('--extension', '-e',
                        help='provide file extension to look for')
    parser.add_argument('--advanced', '-a', action='store_true',
                        help='advanced mode')
    parser.add_argument('--warn', '-w', action='store_true',
                        help='show date inconsistence warning')
    parser.add_argument('--systemtime', '-s', action='store_true',
                        help='use system file modification time')
    parser.add_argument('--fix', '-x', action='store_true',
                        help='fix mtime to resemble filename')
    parser.add_argument('--help', '-h',
                        action='store_true')
    parser.add_argument('--skip', '-i', action='store_true',
                        help='skip inconsistent')
    
    args = parser.parse_args()
    
    if args.format:
        name_format = args.format
    if args.extension:
        extension = args.extension
    if args.systemtime:
        use_time = 'file'
    if args.advanced:
        use_time = 'moov'
    if not args.filename:
        args.filename.append(os.getcwd())
    if args.help:
        print_help()
        sys.exit(0)
    
    filelist = get_file_names(args.filename, extension)
    
    print('')
    if not filelist:
        print('No %s files found.' % extension)
        sys.exit(1)
    
    filetimes = get_file_times(filelist, name_format)
    files_times = list(zip(filelist, filetimes))

    path = ''
    # Use specified mode
    if args.advanced:
        print('Filename'.ljust(20) + '1.File mtime'.ljust(18) + '='.ljust(3) + '2.moov mtime'.ljust(20) + 
              '3.moov ctime'.ljust(20) + '4.trak mtime'.ljust(20) + '5.trak ctime'.ljust(20))
        print('-'*120)
        for filename, times in sorted(files_times):    
            if os.path.dirname(filename) != path:
                path = os.path.dirname(filename)
                print('\n' + path)

            if times['moov'][1] == times['file'][1]:
                eq = '-'
                if args.skip:
                    filelist.remove(filename)
                    filetimes.remove(times)
                    continue
            else:
                eq = 'x'
                
            print(os.path.basename(filename).ljust(20) +
                  times['file'][1].ljust(18) +
                  eq.ljust(3) +
                  times['moov'][1].ljust(20) +
                  times['moov'][0].ljust(20) + 
                  times['trak'][1].ljust(20) +
                  times['trak'][0].ljust(20))
        print('Which time to use? (1-5)')
        selection = input()

    newnames = get_new_filenames(files_times, use_time, extension)
    
    before_after = list(zip(filelist, newnames, filetimes))
    
    print('\nFiles to be renamed:')
    path = ''
    warn = ''
    for before, after, times in sorted(before_after):    
        if os.path.dirname(before) != path:
            path = os.path.dirname(before)
            print('\n' + path)
        if args.warn or args.skip:
            if times['moov'][1] == times['file'][1]:
                warn = '  '
            else:
                warn = 'x '
                if args.skip:
                    newnames.remove(after)
                    filelist.remove(before)
                    continue
        print(os.path.basename(before).ljust(20) + ' -> ' + warn + after)

    print('\nOK? yes/no')
    answer = input()
    
    if answer.startswith('y'):
        for filename, after in zip(filelist, newnames):
            path = os.path.dirname(filename)
            os.rename(filename, os.path.join(path, after)
        print('Done.')
    else:
        print('Nothing to do.')


if __name__ == "__main__":
    main(sys.argv[1:])
