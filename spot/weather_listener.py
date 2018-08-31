#!/usr/bin/python
#
# Test client for the weather data

import socket
import collections
import threading
import asyncore
import logging
import time
from spot.py_utils import userCancel

SERVER_ADDRESS=('0.0.0.0',25000)

def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)
    messageQueue = collections.deque()
    cruncher = messageProcessor(messageQueue)
    #client.add_handler(cruncher.handle)
    keepRunning = threading.Event()
    keepRunning.set()

    client = clientStream(SERVER_ADDRESS,'test_client',keepRunning,messageQueue,retryInterval=10)
    t = threading.Thread(target=cruncher.run,name="Messages",args=(keepRunning,))
    t.daemon=True

    userQuit = userCancel(keepRunning,[t,])

    t.start()
    client.run()

class asyncClientStream(asyncore.dispatcher):
    MAX_BUFFER_LENGTH = 8196
    def __init__(self,host_address,name,keepRunning,notifyQueue=None,retryInterval=10):
        self.log = logging.getLogger('Client (%7s)' % name)
        self.name = name
        self.host = host_address
        self.retryInterval = retryInterval
        self.outbox = collections.deque()
        self.notifyOthers = notifyQueue
        self.handlers = [];
        self.keepGoing = keepRunning
        asyncore.dispatcher.__init__(self)
        self.reconnect()
    def reconnect(self):
        self.disconnect()
        try:
            self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
            self.connect(self.host)
            self.log.info("Connected to %s:%d" % self.getpeername())
            self.connected=True
        except socket.error as e:
            self.log.error("Connection failure to %s:%s"%self.host)
        return self.connected

    def disconnect(self):
        if self.connected:
            self.close()
        self.connected = False

    def add_handler(self,handler):
        self.handlers.append(handler)
    def del_handler(self,handler):
        if handler in self.handlers:
            self.handlers.remove(handler)
    def say(self, message):
        self.outbox.append(message)
    def handle_write(self):
        if not self.outbox:
            return
        message = self.outbox.popleft()
        self.send(message)
    def handle_read(self):
        message = self.recv(self.MAX_BUFFER_LENGTH)
        if self.notifyOthers!=None:
            self.notifyOthers.append(message)
        for handler in self.handlers:
            handler(message)
    def handle_error(self):
        if self.keepGoing.is_set() and self.retryInterval>0:
            self.log.info("Attempting to reconnect in %g seconds",self.retryInterval)
            threading.Timer(self.retryInterval,self.reconnect).start()
    def handle_close(self):
        self.log.info("Socket closed")
        self.handle_error()

    def run(self):
        asyncore.loop()

class messageProcessor(object):
    def __init__(self,Inbox,name='Messenger'):
        self.log = logging.getLogger(name)
        self.count = 0
        self.inbox=Inbox
        self.myname = name

    def handle(self,message):
        print(message)
        self.count+=1
    def run(self,keepRunning):
        while keepRunning.is_set():
            if self.inbox:
                message=self.inbox.popleft()
                self.log.info(message)
            else:
                time.sleep(0.01)

if __name__ == "__main__":
    main()
