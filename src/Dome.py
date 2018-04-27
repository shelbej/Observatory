'''
Dome Class object

-Shelbe Timothy 2018
'''
import serial
import time


class Dome(object):
    def __init__(self):
        self.ser = serial.serial_for_url('socket://192.168.1.20:4660', timeout=1)
        time.sleep(0.800)
        self.dome_state = self.get_dome_state()

    def open(self):
        idx = 0
        ser = self.ser
        dome_state = self.get_dome_state()
        print(dome_state)
        if dome_state == b'0':

            while dome_state != b'y' and idx < 20:
                ser.write(b'b')
                dome_state = self.get_dome_state()
                print(dome_state)
                idx += 1
                time.sleep(0.800)
        dome_state = self.get_dome_state()
        print(dome_state)
        if dome_state == b'':
            time.sleep(.5)
            dome_state = self.get_dome_state()
            print(dome_state)

        if dome_state == b'1':
            print('Dome opened successfully')
        elif dome_state == b'y':
            print('Side B opened successfully')
        else:
            print('Dome state: ', dome_state)

    def close(self):
        idx = 0
        ser = self.ser
        self.dome_state = self.get_dome_state()
        if self.dome_state == b'1':

            while self.dome_state != b'Y' and idx < 20:
                ser.write(b'B')
                self.dome_state = self.get_dome_state()
                print(self.dome_state)
                idx += 1
                time.sleep(0.800)
        self.dome_state = self.get_dome_state()
        print(self.dome_state)
        if dome_state == b'':
            time.sleep(.5)
            self.dome_state = self.get_dome_state()

        if self.dome_state == b'0':
            print('Dome closed successfully')
        else:
            print('Dome state: ', dome_state)

    def disconnect(self):
        self.ser.close()

    def get_dome_state(self):
        if self.ser.read() == b'0':
            state = 'Dome Closed'
        elif self.ser.read() == b'1':
            state = 'B Side Open'
        elif self.ser.read() == b'Y':
            state = 'B Side Closed'
        elif self.ser.read() == b'1':
            state = 'B Side Open'
        return state