#!/usr/bin/python
#
# miscellaneous utilities

# Julian date formula assumes left-to-right evaluation and truncate toward zero
# For python need to use Python 3 division (import __future__) and int()
# From the Fortran:
#    K1=(Month-14)/12
#    JULIAN = Day-32075+1461*(Year+4800+K1)/4+367*(Month-2-K1*12)/12-3*((Year+4900+K1)/100)/4
from __future__ import division
from datetime import datetime, timedelta
from time import gmtime,strftime
import signal, sys

def ts_mjd(ts):
    return 40587+ts/86400.
def tm_mjd(tm):
    y,m,d=tm[0:3]
    return ymd_MJD(y,m,d)+(tm[5]+60*(tm[4]+60*tm[3]))/86400.    
def tm_timestamp(tm):
    y,m,d=tm[0:3]
    return ymd_Y70(y,m,d)*86400+(tm[5]+60*(tm[4]+(60*tm[3])))
def ymd_JD(Y,M,D):
    return D+int((1461*(Y+4800+int((M-14)/12)))/4)+int((367*(M-2-int((M-14)/12)*12))/12)-int((3*int((Y+4900+int((M-14)/12))/100))/4)-32075
def ymd_MJD(Y,M,D):
    return D+int((1461*(Y+4800+int((M-14)/12)))/4)+int((367*(M-2-int((M-14)/12)*12))/12)-int((3*int((Y+4900+int((M-14)/12))/100))/4)-2432076
def ymd_Y70(Y,M,D):
    return D+int((1461*(Y+4800+int((M-14)/12)))/4)+int((367*(M-2-int((M-14)/12)*12))/12)-int((3*int((Y+4900+int((M-14)/12))/100))/4)-2472663
def local_time_str(t):
    return datetime.fromtimestamp(t).isoformat(" ")
def utc_time_str(t):
    return datetime.utcfromtimestamp(t).isoformat(" ")
def sql_time_str(t):
    return datetime.utcfromtimestamp(t).isoformat(" ")
def utc_offset(t):
    return (datetime.utcfromtimestamp(t)-datetime.fromtimestamp(t)).total_seconds()
def fullfile(p):
    return "/".join(p)
    
class userCancel(object):
    def __init__(self,stopper,workers):
        self.cancel = False
        self.stopper = stopper
        self.workers = workers
        signal.signal(signal.SIGINT,self)
    def __call__(self,signum,frame):
        self.cancel=True
        self.stopper.clear()
        for worker in self.workers:
            worker.join()
            sys.exit(0)
    def add(self,worker):
        self.workers.append(worker)
    def remove(self,worker):
        if worker in self.workers:
            self.workers.remove(worker)
