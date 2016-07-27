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
    Get filelist to process
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


def get_new_filenames(files_and_timestamps, use_time, extension):
    """
    Create list of new filenames appending index when new name
    already exists
    """
    new_names = []
    file_extension_check = re.compile('(\.' + extension + ')$', re.I)
    
    for old_filename, file_timestamp in files_and_timestamps:
        current_file_extension = file_extension_check.search(old_filename).group(1)
        current_file_extension_length = len(current_file_extension)
        # Create new name
        this_file_timestamp = file_timestamp[use_time][1]
                
        if this_file_timestamp == 0:
            # No creation time for this file found
            # Will try to use old name. Adding index if it overlaps
            # with new filenames
            new_filename = old_filename
        else:
            new_filename = this_file_timestamp + current_file_extension
                       
        file_index = 0
        new_name_without_index = new_filename[:-current_file_extension_length]

        # If new filename already exists in new_names list append index to it
        while new_filename in new_names:
            file_index += 1
            new_filename = new_name_without_index + '-' + str(file_index) + current_file_extension
        new_names.append(new_filename)
    
    return new_names


def get_file_timestamps(files, timestamp_format):
    """
    Get list of system and QT timestamps from files
    """
    timestamps = []      # list of different timestamps for files

    for filename in files:
        file_timestamps = {'file': [0, 0]}  # Will contain all time values we will find
    
        # Get file mtime
        file_timestamps['file'][1] = os.path.getmtime(filename)
        
        # Get moov timestamps
        file_timestamps.update(get_moov_time(filename))
        
        # Format all timestamps according to provided template
        try:
            format_time(file_timestamps, timestamp_format)
        except ValueError:
            print('Error in time format "{0}."'.format(timestamp_format))
            sys.exit(1)
        
        timestamps.append(file_timestamps)
    
    return timestamps


def format_time(timestamps, time_format):
    """
    Format timestamps according to provided template
    """
    for timestamp_type in timestamps:
        for time_item in range(len(timestamps[timestamp_type])):
            timestamps[timestamp_type][time_item] = time.strftime(
                time_format,
                time.localtime(timestamps[timestamp_type][time_item])
            )


def read_times(filename):
    """
    Read creation and modification time given the beginning of atom
    """
    QT_EPOCH = 2082844800
    filename.seek(4, 1)
    ctime = struct.unpack('>I', filename.read(4))[0] - QT_EPOCH
    mtime = struct.unpack('>I', filename.read(4))[0] - QT_EPOCH
    return [ctime, mtime]


def get_moov_time(filename):
    """
    Get movie creation time from moov atom. Returns 0 in case of error.
    """
    # atom: header, length after dates
    mov_atoms = {b'moov': {'header': b'mvhd', 'size': 88}}
    moov_atoms = {b'trak': {'header': b'tkhd', 'size': 72},
                  b'mdia': {'header': b'mdhd', 'size': 12}}
    # moov ctime/mtime, trak ctime/mtime, mdia ctime/mtime
    timestamps = {'moov': [0, 0], 'trak': [0, 0], 'mdia': [0, 0]}
    
    with open(filename, 'r+b') as movie:
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
                # Check for correct header and read timestamps
                if header == atoms[atom_type]['header']:
                    timestamps[atom_type.decode()] = read_times(movie)

                # seek to the end of atom
                movie.seek(atoms[atom_type]['size'], 1)

            # If found moov continue to inner moov atoms
            if atom_type == b'moov':
                atoms = moov_atoms

            else:
                if atom_size < 8:
                    break
                movie.seek(atom_size - 8, os.SEEK_CUR)

    return timestamps
            

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
    
    file_timestamps = get_file_timestamps(filelist, name_format)
    files_and_timestamps = list(zip(filelist, file_timestamps))

    path = ''
    # Use specified mode
    if args.advanced:
        print('Filename'.ljust(20) + '1.File mtime'.ljust(18) + '='.ljust(3) + '2.moov mtime'.ljust(20) + 
              '3.moov ctime'.ljust(20) + '4.trak mtime'.ljust(20) + '5.trak ctime'.ljust(20))
        print('-'*120)
        for filename, times in sorted(files_and_timestamps):
            if os.path.dirname(filename) != path:
                path = os.path.dirname(filename)
                print('\n' + path)

            if times['moov'][1] == times['file'][1]:
                eq = '-'
                if args.skip:
                    filelist.remove(filename)
                    file_timestamps.remove(times)
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

    newnames = get_new_filenames(files_and_timestamps, use_time, extension)
    
    before_after = list(zip(filelist, newnames, file_timestamps))
    
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
            os.rename(filename, os.path.join(path, after))
        print('Done.')
    else:
        print('Nothing to do.')


if __name__ == "__main__":
    main(sys.argv[1:])
