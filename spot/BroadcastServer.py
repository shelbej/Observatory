#!/usr/bin/python
#
# A simple broadcast  server. A single client is the seed
# client that receives messages, and broadcasts them to
# all other clients

import asyncore
import collections
import logging
import socket

MAX_BUFFER_LENGTH = 16535

#-------------------------------------------------------------
# Listening server
class BroadcastServer(asyncore.dispatcher):
    log = logging.getLogger('broadcaster')
    def __init__(self,address=('0.0.0.0',0),name='noname'):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.setsockopt='192.168.1.20:4662'
        self.bind(address)
        self.listen(1)
        self.remote_clients=[]
        self.myname = name
        self.log.info( self.myname + " starting at " + str(address) )
    def handle_accept(self):
        socket, addr = self.accept()  # accepting remote connection
        self.log.info('Accepted client at %s',addr)
        self.remote_clients.append(RemoteClient(self,socket,addr))
    def handle_read(self):
        self.log.debug('Received message: %s', self.read())
    def broadcast(self,message):
        self.log.debug('Broadcasting to %2d clients: %s',len(self.remote_clients), message)
        for remote_client in self.remote_clients:
            remote_client.say(message)
    def remove_client(self,client):
        self.remote_clients.remove(client)      
    def run(self):
        asyncore.loop()

#-----------------------------------------------------------------
# Primary Client - initiates a connection
class PrimaryClient(asyncore.dispatcher):
   def __init__(self,host_address,name):
      asyncore.dispatcher.__init__(self)
      self.log = logging.getLogger('Client (%7s)' % name)
      self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
      self.name = name
      self.log.info('Connecting to host at %s',host_address)
      self.connect(host_address)
      self.outbox = collections.deque()
   def say(self, message):
      self.outbox.append(message)
      self.log.debug('Enqueued message: %s',message)
   def handle_write(self):
      if not self.outbox:
         return
      message = self.outbox.popleft()
      self.send(message)
   def handle_read(self):
      message = self.recv(MAX_BUFFER_LENGTH)
      self.log.debug('Received message: %s', message)

#------------------------------------------------------------------
# Remote Client - this is the accepted socket connection
class RemoteClient(asyncore.dispatcher):
   def __init__(self, host, socket, address):
      asyncore.dispatcher.__init__(self, socket)
      self.host = host
      self.outbox = collections.deque()
      self.log = logging.getLogger('(%s:%d)' % address)
   def say(self, message):
      self.outbox.append(message)
   #def handle_read(self):
      #client_message = self.recv(MAX_BUFFER_LENGTH)
      #if client_message=='':
      #   print "Revc: closing connection to ",self.getpeername()
      #   self.close()
      
   def handle_write(self):
      if not self.outbox:
         return
      message = self.outbox.popleft()
      sent=self.send(message)
      #if sent==0:
      #   print "Send: closing connection to ",self.getpeername()
      #   self.close()
   def handle_close(self):
      self.log.info('Connection closed')
      self.host.remove_client(self)


#------------------------------------------------------------------


