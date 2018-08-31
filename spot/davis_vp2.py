#!/usr/bin/env python
#
# Class to handle comms with a Davis Vantage Pro 2 weather station
# 2016-12-13 GMM Added protection around packing in loop_data. This killed the collection
#                thread at some point. Maybe I should be checking the loop data checksum

import socket
import logging
from math import log
import time
import datetime
import collections, struct
import threading
import json
from spot.py_utils import utc_offset, userCancel
from spot.weather_archiver import weather_archiver
from spot.weather_box_average import weather_box_average
from spot.BroadcastServer import BroadcastServer
from spot.davis_crc import crc_check
from spot.spot_weather_db import spot_env_site
from spot.weatherStatus import WeatherStatus


AVERAGING_SPAN = 60   # seconds for shifting box average
ARCHIVE_LOC    = 'data/spot/weather'
ROLLOVER_HOUR  = 0    # UTC hour for file roll-over

TCP_SERVER    = ('0.0.0.0',15100)
SITE_CODE     = 50
DAVIS_CONSOLE = {'Name':'ATC_Davis','Address':('192.168.1.20',4662)}
LOG_LEVEL     = logging.INFO
LOG_PATH      = 'data/spot/logs'

LF      = b'\x0A'
CR      = b'\x0D'
LFCR    = LF + CR
ACQ     = b'\x06'
LOOP    = b"LOOP 1" + LF
LOOPACQ = ACQ + b"LOO"

def test():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=LOG_LEVEL)
    com           = tcp_com_stream(DAVIS_CONSOLE['Address'],name=DAVIS_CONSOLE['Name'],connectAtStart=False)
    weatherq      = collections.deque()
    dataReady     = threading.Event()
    keepRunning   = threading.Event()
    keepRunning.set()

    wsql          = spot_env_site()
    waccum        = weather_box_average(AVERAGING_SPAN,wsql)
    warchive      = weather_archiver(ARCHIVE_LOC,ROLLOVER_HOUR,SITE_CODE,RAW=True)
    dvp           = davis_weather_interface(com,weatherq,dataReady,keepRunning)
    server        = BroadcastServer(TCP_SERVER)
    wconsole      = WeatherStatus(AVERAGING_SPAN, keepRunning)

    # Thread to manage socket connection with Davis weather station;
    # accumulates data packets in queue
    t1            = threading.Thread(target=dvp.worker,name='Davis Interface')
    t1.daemon     = True

    # Thread waits for new weather data (blocking), then forwards to
    # box averager, archiver, and broadcast server
    t2  = threading.Thread(target=update_weather_data,name="Data Update",args=(weatherq,dataReady,keepRunning,waccum,warchive))#,server))
    t2.daemon = True

    # Thread that inserts averaged data into SQL server at configured cadence
    t3  = threading.Thread(target=wsql.worker,name="SQL Thread",args=(AVERAGING_SPAN,keepRunning,))
    t3.daemon = True

    t4 = threading.Thread(target=wconsole.worker,name="Weather Console",args=(AVERAGING_SPAN,keepRunning,))
    t4.daemon = True

    userQuit = userCancel(keepRunning,[t1,t2,t3])

    t1.start()
    t2.start()
    t3.start()
    t4.start()
    server.run()
    #signal.pause()

def weather_message(message):
    msg = json.dumps(message)+"\n"
    #return struct.pack("<L",len(msg))+msg
    return msg

def update_weather_data(weatherq,dataReady,keepRunning,waccum,warchive):#,server):
    while keepRunning.is_set():
        if dataReady.wait():
            if weatherq:
                weather_rec = weatherq.popleft()
                # if (weather_rec.packed != None):
                waccum.accumulate(weather_rec.data)
                warchive.archive(weather_rec)
                #server.broadcast(weather_message(weather_rec.data))

            dataReady.clear()

class tcp_com_stream:
    def __init__(self,remote_address,name=None,connectAtStart=False):
        self.host_address = remote_address
        if name==None:
            self.name="{:s}@{:s}:{:d}".format('stream',remote_address[0],remote_address[1])
        else:
            self.name="{:s}@{:s}:{:d}".format(name,remote_address[0],remote_address[1])
        self.log = logging.getLogger(self.name)
        self.connected = False
        if connectAtStart:
            self.connect()

    def connect(self):
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        try:
            self.sock.connect(self.host_address)
            self.connected = True
        except socket.error as e:
            self.log.error("Connection failed: %s" % e[1])
            self.connected = False
        return self.connected

    def disconnect(self):
        self.sock.close()
        self.connected = False

    def recycle(self):
        self.disconnect()
        self.connect()

    def put(self,message):
        n = self.sock.sendall(message)
        return n

    def get(self,N,timeout=123456):
        if timeout!=123456:
            old_timeout = self.sock.gettimeout()
            self.sock.settimeout(timeout)
        try:
            msg=self.sock.recv(N)
            timeOut = False
        except socket.timeout:
            self.log.warn("Data receive timeout")
            timeOut = True
            msg = ''

        if timeout!=123456:
            self.sock.settimeout(old_timeout)
        return msg,timeOut

def condensationTemperature(TF,RH):
    # Based on the Magnus approximation (see Dew_Point on wikipedia for summary)
    a  = 6.1121; b = 17.368; c = 237.7;
    TC = (TF-32.)*(5./9.)
    #print(TF, RH, (RH/100.0)+(b*TC)/(c+TC))
    G  = log(max((RH/100.0)+(b*TC)/(c+TC), 1))
    return ((c*G)/(b-G))*(9./5.)+32.0

class loop_data(object):
    rfmt = struct.Struct('<bHHBHBBHBHBB')
    wfmt = struct.Struct('<dihHHHHHHHHHHHHH')
    def __init__(self,t,d):
        self.log = logging.getLogger('loop_data')
        self.t = t
        self.dut = int(utc_offset(t))
        self.loop_data = d
        #v=self.rfmt.unpack(d[3]+d[7:18]+d[33]+d[41:43]+d[89:91])
        Tout = struct.unpack('<H', d[12:14])[0]/10.
        Hum = struct.unpack('<b', d[33:34])[0]
        Bar = struct.unpack('<H', d[7:9])[0]/1000.
        Ws = struct.unpack('<b', d[14:15])[0]
        Wsa = struct.unpack('<b', d[15:16])[0]
        Wd = struct.unpack('<H', d[16:18])[0]
        Rain = struct.unpack('<H', d[41:43])[0]/100.

        # Tin   = v[2]/10.
        # RHin  = v[3]
        # Tout  = v[4]/10.
        # RHout = v[8]
        # TdIn  = condensationTemperature(Tin,RHin)
        TdOut = condensationTemperature(Tout, Hum)
        self.data = {'timestamp'         : t           ,
                     'utcoffset'         : self.dut    ,
                     'timestr'           : datetime.datetime.now().strftime('%Y-%b-%d %H:%M:%S.%f') ,
                     'barTrend'          : 0        , # pressure trend, -60,-40,-20,0,20,40,60 (rapidly decreasing to rapidly increasing
                     'barometer'         : Bar  , # pressure, inHG
                     'insideTemperature' : 0         , # degF
                     'insideHumidity'    : 0        , # %
                     'insideDewTemp'     : 0        , # degF
                     'outsideTemperature': Tout        , # degF
                     'outsideHumidity'   : Hum       , # %
                     'outsideDewTemp'    : TdOut       , # degF
                     'windSpeed'         : Ws        , # mph
                     'windSpeedAvg'      : Wsa        , # mph
                     'windDirection'     : Wd        , # 1-360, 0=no data
                     'rainRate'          : Rain    , # in/day
                     'forecastCode'      : 0      , # see icon codes in manual
                     'forecastRule'      : 0       , # see manual
                     }


class davis_weather_interface:
    def __init__(self,com,outbox,dataReady,keepRunning):
        self.com = com
        self.log = logging.getLogger('davis_interface')
        self.outbox  = outbox
        self.dataReady = dataReady
        self.keepRunning = keepRunning

    def wake_up(self,attempts=5):
        awake = False
        while (attempts>0 and not awake):
            self.com.put(LF)
            ret,timeOut=self.com.get(2,1.2)
            awake = (ret==LFCR and not timeOut)
            attempts -= 1
        return awake
    def get_loop_data(self):
        self.com.put(LOOP)
        data,timeOut=self.com.get(100,1.2)
        return data,timeOut
    def publish(self,obj):
        # NOTE: Could move logic from update_weather_data thread here
        self.outbox.append(obj)
    def worker(self,time_interval=2):
        """ The worker runs forever and sets the dataReady event
            when loop data is available. It will block waiting on
            loop data, as well as for connection and re-connection
            attempts to the Davis weather station.
        """
        self.dataReady.clear()
        while self.keepRunning.is_set():
            if self.com.connect():
                if (not self.wake_up()):
                    self.log.error('Weather station is not awake')
                else:
                    nextt = int(time.time()/2)*2 + time_interval
                    gettingData = True
                    while self.keepRunning.is_set() and gettingData:
                        time.sleep(nextt-time.time()-0.00195)
                        t1=time.time()
                        data,timeOut = self.get_loop_data()
                        if timeOut:
                            gettingData = False
                        else:
                            if data[0:4]==LOOPACQ and crc_check(data[1:])==0:
                                #t2=time.time()
                                #self.log.debug("Loop data received req:%s rvc:%s",time_str(t1),time_str(t2))
                                self.publish(loop_data(t1,data[1:]))
                                self.dataReady.set()
                            elif data[0:4]!=LOOPACQ:
                                self.log.error("Start of loop data error")
                            else:
                                self.log.error("Loop data failed checksum")
                            nextt = nextt+time_interval
                # If we drop back here that means we have to disconnect and retry
                self.com.disconnect()

def davis_debug(d):
    return "%s P %6.3f T %4.1f R %3.0f Td %4.1f W %5.2f" % ( d['timestr'],d['barometer'],d['outsideTemperature'],d['outsideHumidity'],d['outsideDewTemp'],d['windSpeed'])

if __name__=="__main__":
    test()

