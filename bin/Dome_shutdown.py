#~/anaconda3/bin/python
from spot.Dome import Dome
import datetime
import os
from io import BufferedWriter, FileIO
import logging

log = logging.getLogger('shutdown')
logfile = '/Users/e298770/Developer/SpOT/DavisVP2/data/spot/weather/status_' + datetime.datetime.now().strftime('%m-%d-%y') + '.log'
try:
    if os.path.exists(logfile):
        fd = BufferedWriter(FileIO(logfile, 'ab'))
    else:
        fd = BufferedWriter(FileIO(logfile, 'wb'))
except IOError:
    log.error("Cannot create log file %s" % logfile)

dome = Dome()
state = dome.get_dome_state(byte=False)
if state != 'Dome Closed':
    dome.close()
dome.refresh()
state = dome.get_dome_state(byte=False)
fd.write(bytes(datetime.datetime.now().strftime('%m-%d-%y %H:%M:%S '), encoding='utf-8'))
if state == 'Dome Closed':
    fd.write(bytes(state+' - Shutdown Complete\n', encoding='utf-8'))