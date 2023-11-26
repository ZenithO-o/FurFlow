import serial
from run import setup_serial
import random
import time

options = [b'dn1: 31.09/50.00/0/42.50/1004.04/13\n',
           b'dn2: 32.09/20.00/0/46.50/1004.04/45\n',
           b'dn2: 21.09/30.00/0/44.50/1004.04/18\n',
           b'dn1: 33.09/40.00/0/39.50/1004.04/12\n']

with setup_serial(port='COM3') as ser:
    for option in options:
        ser.write(option)
        time.sleep(1)
