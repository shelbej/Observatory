'''
Dome Class object
Provides methods to communicate with the Astrohaven Dome

-Shelbe Timothy, July 2018
'''
import serial
import time

dome_loc ='socket://192.168.1.20:4660'

class Dome(object):
    def __init__(self):
        self.ser = serial.serial_for_url(dome_loc, timeout=1)

    def open(self):
        self.dome_state = self.get_dome_state()

        if self.ser.is_open:
            idx = 0
            while idx < 15:
                self.ser.write(b'b')
                time.sleep(.5)
                idx += 1
            self.dome_state = self.get_dome_state()
            if self.dome_state == b'' or self.dome_state == b'b':
                self.refresh()
                self.dome_state = self.get_dome_state()

        if self.dome_state == b'1':
            print('Dome opened successfully')
        elif self.dome_state == b'y':
            print('Side B opened successfully')
        else:
            print('Dome state: ', self.dome_state)

    def close(self):
        self.dome_state = self.get_dome_state()

        if self.ser.is_open:
            idx = 0
            while idx < 15:
                self.ser.write(b'B')
                time.sleep(.5)
                idx += 1

            self.dome_state = self.get_dome_state()
            while self.dome_state == b'' or self.dome_state == b'B':
                self.refresh()
                self.dome_state = self.get_dome_state()
        if self.dome_state == b'1':
            print('Dome Ajar, Reattempt Dome Close')
            idx = 0
            while idx < 15:
                self.ser.write(b'B')
                time.sleep(.5)
                idx += 1
        elif self.dome_state == b'0' or self.dome_state == b'Y':
            print('Dome closed successfully')
        else:
            print('Dome state: ', self.dome_state)

    def disconnect(self):
        self.ser.close()

    def refresh(self):
        self.ser.close()
        self.ser = serial.serial_for_url(dome_loc, timeout=1)

    def get_dome_state(self, byte=True):
        self.ser.read()
        while self.ser.read() == b'':
            self.ser.read()
        if self.ser.read() == b'0':
            state = 'Dome Closed'
        elif self.ser.read() == b'1':
            state = 'B Side Ajar'
        elif self.ser.read() == b'Y':
            state = 'B Side Closed'
        elif self.ser.read() == b'y':
            state = 'B Side Open'
        else:
            state = 'Unknown State: ' + str(self.ser.read())
        print(state)
        if byte:
            return self.ser.read()
        else:
            return state