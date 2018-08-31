#!/usr/bin/python

import socket
import struct
import threading
import Queue

class threadededTCPClient(threading.Thread):
    def __init__(self,Inbox=None,Outbox=None):
        super(threadedTCPClient,self).__init__()
        self._cmd = Inbox or Queue.Queue()
        self._reply = Outbox or Queue.Queue()
        self.alive = threading.Event()
        self.alive.set()
        self.socket = None
        self.handlers = {
            clientCommand.CONNECT: self._handle_CONNECT,
            clientCommand.CLOSE: self._handle_CLOSE,
            clientCommand.SEND: self._handle_SEND,
            clientCommand.RECEIVE: self._handle_RECEIVE,
        }
    def run(self):
        while self.alive.isSet():
            try:
                # Check the command queue
                # Time out is so we can keep checking self.alive
                cmd = self._cmd.get(True,0.1)
                self.handlers[cmd.type](cmd)
            except Queue.Empty as e:
                continue
    def join(self,timeout=None):
        self.alive.clear()
        threading.Thread.join(self, timeout)
    def _handle_CONNECT(self,cmd):
        try:
            self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.socket.connect((cmd.data[0],cmd.data[1]))
            self._reply.put(self._success_reply())
        except IOError as e:
            self._reply.put(self._error_reply(str(e)))
    def _handle_CLOSE(self, cmd):
        self.socket.close()
        self._reply.put(clientReply(clientReply.SUCCESS))
    def _handle_SEND(self, cmd):
        header = struct.pack('<L',len(cmd.data)+1)
        try:
            self.socket.sendall(header+cmd.data+"\n")
            self._reply.put(self._success_reply())
        except IOError as e:
            self._reply.put(self._error_reply(str(e)))
    def _handle_RECEIVE(self,cmd):
        try:
            header_data = serv._recv_n_bytes(4)
            if len(header_data) == 4:
                msg_len = struct.unpack('<L',header_data)[0]
                data = self._recv_n_bytes(msg_len)
                if len(data)==msg_len:
                    self._reply.put(self._success_reply(data))
                    return
            self._reply.put(self._error_replay('Socket closed prematurely'))
        except IOError as e:
            self._reply.put(self._error_reply(str(e)))
    def _recv_n_bytes(self,n):
        data = ''
        while len(data)<n:
            chunk = self.socket.recv(n-len(data))
            if chunk=='':
                break
            data += chunk
        return data
    def _error_reply(self,errstr):
        return ClientReply(ClientReply.ERROR,errstr)
    def _success_reply(self,data=None):
        return ClientReply(ClientReply.SUCCESS,data)

class ClientCommand(object):
    CONNECT, SEND, RECEIVE, CLOSE = range(4)
    def __init__(self,type,data=None):
        self.type = type
        self.data = data

class ClientReply(object):
    ERROR, SUCCESS = range(2)
    def __init__(self,type,data=None):
        self.type = type
        self.data = data
