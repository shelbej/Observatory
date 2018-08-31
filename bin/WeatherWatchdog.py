#!~/anaconda3/bin/python
'''
WeatherWatchdog Cron Script
Main Driver script for multiple Weather Monitoring threads:
spot_env_site - builds weather record in python dictionary format
weather_box_average - box averages weather record every 60 sec
weather_archiver - robust achiver, saves .log & .xlsx files
tcp_com_stream -
davis_weather_interface -
update_weather_data
WeatherStatus - check conditions to open/close dome
BroadcastServer - not sure, but threads die without it
-Shelbe Timothy, July 2018
'''
import logging

import collections
import threading
from spot.spot_weather_db import spot_env_site
from spot.weatherStatus import WeatherStatus
from spot.BroadcastServer import BroadcastServer
from spot.davis_vp2 import tcp_com_stream, weather_box_average, weather_archiver
from spot.davis_vp2 import davis_weather_interface, update_weather_data

AVERAGING_SPAN = 60  # seconds for shifting box average
ARCHIVE_LOC = 'data/spot/weather'
ROLLOVER_HOUR = 0  # UTC hour for file roll-over

TCP_SERVER = ('0.0.0.0', 15100)
SITE_CODE = 50
DAVIS_CONSOLE = {'Name': 'ATC_Davis', 'Address': ('192.168.1.20', 4662)}
LOG_LEVEL = logging.INFO
LOG_PATH = 'data/spot/logs'

LF = b'\x0A'
CR = b'\x0D'
LFCR = LF + CR
ACQ = b'\x06'
LOOP = b"LOOP 1" + LF
LOOPACQ = ACQ + b"LOO"

def after_timeout():
    print('First Run complete')
    raise SystemExit

def main():

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=LOG_LEVEL)
    com = tcp_com_stream(DAVIS_CONSOLE['Address'], name=DAVIS_CONSOLE['Name'], connectAtStart=False)
    weatherq = collections.deque()
    dataReady = threading.Event()
    keepRunning = threading.Event()
    keepRunning.set()

    wsql = spot_env_site()
    waccum = weather_box_average(AVERAGING_SPAN, wsql)
    warchive = weather_archiver(ARCHIVE_LOC, ROLLOVER_HOUR, SITE_CODE, RAW=True)
    dvp = davis_weather_interface(com, weatherq, dataReady, keepRunning)
    server = BroadcastServer(TCP_SERVER)
    wstatus = WeatherStatus(AVERAGING_SPAN, keepRunning)


    # Thread to manage socket connection with Davis weather station;
    # accumulates data packets in queue
    t1 = threading.Thread(target=dvp.worker, name='Davis Interface')
    t1.daemon = True

    # Thread waits for new weather data (blocking), then forwards to
    # box averager, archiver, and broadcast server
    t2 = threading.Thread(target=update_weather_data, name="Data Update",
                          args=(weatherq, dataReady, keepRunning, waccum, warchive))#, server))
    t2.daemon = True

    # Thread that inserts averaged data into SQL server at configured cadence
    t3 = threading.Thread(target=wsql.worker, name="SQL Thread", args=(AVERAGING_SPAN, keepRunning,))
    t3.daemon = True

    t4 = threading.Thread(target=wstatus.worker, name="Weather Status", args=(AVERAGING_SPAN, keepRunning,))
    t4.daemon = True
    #userQuit = userCancel(keepRunning, [t1, t2, t3, t4])
    #timer = threading.Timer(AVERAGING_SPAN, after_timeout)
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    server.run()
    #timer.start()

    return 0

main()
