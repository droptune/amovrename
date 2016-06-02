# Advanced MOV Renamer

Python script to rename .MOV files (QuickTime) using video modification date in MOV metadata.

This -> **IMGP3098.mov** becomes this -> **20160602-1430.mov**

## Usage
`python amovrename.py [-h] [-a] [-s] [-w] [-i] [-e EXTENSION] [-f "FORMAT"] FILES`  

| Option | Description |
| --- | --- |
| -h, --help | show help|
| FILES | files, or path to files|
| -a, --advanced | advanced mode which shows several options of metadata dates to use|
| -f "FORMAT", --format "FORMAT" | accepts standard datetime variables to use as new name (see below)|
| -s | Use system file modification date|
| -w | Warn when files metadata dates is inconsistent with it's modification date (will show x by the name), so you can|
| --skip, -i | Will skip files with dates inconsistencies as indicated in previous point|
| -e EXTENSION | Rename files with extensions different from MOV. It's regexp, so you can specify several options. Usually I use `-e 'MOV|MTS' -s` to rename videos from my camera, which obviously don't contain QT metadata|

By default script uses QuickTime moov header movie modification time, because usually it contains the right thing, but in some cases it's not right (that's why I had to write this script).

You can choose several options to set what time of movie to use for naming.

Default format of new names is %Y%m%d-%H%M which results in files 20160120-1305.mov. You can change this using standard datetime syntax as described at [Python docs](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior), e.g.:
```
amovrename.py -f "%b %d_%I%p - Autumn vacation" ./
'IMGP3098.mov' -> 'Jun 02_02pm - Autumn vacation.mov'
```

## More info

I like when my video/photo files have some meaningful names containing dates, so I can sort and manage them chronologically.

Generally dates inside quicktime files should be the most accurate way to determine the date video was created. But there is a known issue with iPhone 5s (maybe in others) that sometimes writes creation time that is offset by several hours (day and month usually stay the same), while modification time can stay true or becomes also offset. In this cases I use system file modification date, which is also what Windows shows as file date for mov files when you use table view. But it's not reliable way (which almost always works for me anyway) since there is no guarantee that it was not changed since video creation. So if you really care about date and it is important to get it down to minute such cases must be accounted. This util when used with -w key will show warnings when it detects inconsistency between system file modification date and quicktime metadata modification time and allows you to choose which one to use for naming.

Inside quicktime metadata itself there are several places where creation time is stored:
- the global movie creation/modification time in mvhd header of moov atom
- track creation/modification time in tkhd header of trak atom for each track in file
- media creation/modification time in mdhd header of media atom for media inside each track

Usually all these are the same. At least when file is produced by any kind of camera.
