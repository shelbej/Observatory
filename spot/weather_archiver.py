#!/usr/bin/python
#
# Rotating file saver for weather data
# Basically should be a robust process with fault management
# Time throughout the module is a timestamp as returned (for example)
# by time.time(). This is usually seconds since 1/1/1970 00:00:00 UTC
# on most systems

import os, logging
from io import BufferedWriter, FileIO
from time import gmtime, strftime
import json
    
class weather_archiver(object):
    def __init__(self, ARCHIVE_ROOT_PATH='./', UTC_ROLLOVER_HOUR=0, SITE_ID=50, RAW=False):
        self.fd               = None
        self.fdRaw            = None
        self.rollover_time    = None
        self.rollover_ref     = UTC_ROLLOVER_HOUR*3600
        self.filePrefix       = "Site_%03d_Weather" % SITE_ID
        self.root_archive_dir = ARCHIVE_ROOT_PATH
        self.raw              = RAW
        self.log              = logging.getLogger('weather_archiver')

    def archive(self, loop_data):
        self.file_rollover(loop_data.t)
        if self.fd!=None:
            self.fd.write(bytes(json.dumps(loop_data.data), encoding='utf-8')+b'\n')

    def file_rollover(self,t):
        """ rollover the file if necessary
        """
        if self.rollover_time==None:
            # Not initialized yet... set the current day and next rollover
            self.rollover_time    = self.rollover_ref+int((t-self.rollover_ref)/86400)*86400

        if self.rollover_time<=t:
            # Close the currently open file
            if (self.fd!=None):
                self.log.info("Closing %s" % self.fd.name)
                self.fd.close()
                self.fd = None

            Day         = strftime("%Y_%m_%d",gmtime(self.rollover_time))
            Year        = Day[0:4]
            fileBase    = "%s_%s" % (self.filePrefix,Day)
            yearPath    = os.path.join(self.root_archive_dir,Year)
            if not os.path.exists(yearPath):
                try:
                    os.makedirs(yearPath)
                except os.error as e:
                    self.log.error("Cannot create %s : %s" % (yearPath,str(e)))
                    self.log.error("Redirecting to /tmp")
                    yearPath = os.path.join('/tmp',Year)
                    if not os.path.exist(yearPath):
                        try:
                            os.makedirs(yearPath)
                        except os.error as e:
                            self.log.error("Cannot create %s either: %s" % ( yearPath, str(e) ))
            if os.path.exists(yearPath):
                filePath = os.path.join(yearPath,fileBase+".log")
                try:
                    if os.path.exists(filePath):
                        self.fd = BufferedWriter(FileIO(filePath,'ab'))
                    else:
                        self.fd = BufferedWriter(FileIO(filePath,'wb'))
                except IOError:
                    self.log.error("Cannot create log file %s" % filePath)
            if os.path.exists(yearPath) and self.raw:
                filePath = os.path.join(yearPath,fileBase+".raw")
                try:
                    if os.path.exists(filePath):
                        self.fdRaw = BufferedWriter(FileIO(filePath,'ab'))
                    else:
                        self.fdRaw = BufferedWriter(FileIO(filePath,'wb'))
                except IOError:
                    self.log.error("Cannot create log file %s" % filePath)

            self.rollover_time += 86400
