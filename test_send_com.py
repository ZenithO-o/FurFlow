import serial
import pathlib
import time
import json

file_path = pathlib.Path(__file__).parent.resolve()

with open(file_path/'config.json', encoding='utf-8') as json_file:
    config = json.load(json_file)

options = [b'dn1: 31.09/50.00/0/42.50/1004.04/13\n',
           b'dn2: 32.09/20.00/0/46.50/1004.04/45\n',
           b'dn2: 21.09/30.00/0/44.50/1004.04/18\n',
           b'dn1: 33.09/40.00/0/39.50/1004.04/12\n']

ser_config = config['Serial']
ser_config['port'] = 'COM3'

with serial.Serial(**ser_config) as ser:
    for option in options:
        ser.write(option)
        time.sleep(1)
