import asyncio
import telegram
import os
import pathlib
import serial
import time
import datetime
import pytz
import re
import json
import multiprocessing
from multiprocessing.connection import PipeConnection
from multiprocessing import Process, Pipe
import serial.tools.list_ports
from dotenv import load_dotenv

file_path = pathlib.Path(__file__).parent.resolve()

with open(file_path/'config.json', encoding='utf-8') as json_file:
    config = json.load(json_file)

def serial_loop(serial_info, send_pipe: PipeConnection):
    serial_context = setup_serial(port=serial_info, timeout=6)

    devices_dict = {d:None for d in config['Devices']}
    while True:
        res = listen_to_port(serial_context)
        if not res:
            continue

        res_dict = parse_serial_result(res)

        device = res_dict.get('device')
        devices_dict.update({device: res_dict})

        if all(devices_dict.values()):
            results = sorted(devices_dict.values(), key= lambda x: x['device'])
            send_pipe.send(results)
            devices_dict = {d:None for d in config['Devices']}

def telegram_loop(bot_info, recieve_pipe: PipeConnection):
    bot_context = telegram.Bot(bot_info)

    while True:
        answer = recieve_pipe.recv()
        message = result_to_telegram(answer)
        asyncio.run(send_updates(bot_context, message))

def main(serial_info, bot_info):
    t_pipe, s_pipe = Pipe(duplex=False)
    serial_p = Process(target=serial_loop, args=(serial_info, s_pipe))
    telegr_p = Process(target=telegram_loop, args=(bot_info, t_pipe))

    serial_p.start()
    telegr_p.start()

    serial_p.join()
    telegr_p.join()
    print('Main function ended!')

async def send_updates(bot_context: telegram.Bot, message: str):
    chat_id = os.environ.get('CHAT_ID')
    async with bot_context:
        await bot_context.send_message(text=message, chat_id=chat_id)

def listen_to_port(serial_context: serial.Serial):
    with serial_context as ser:
        return ser.readline()

def parse_serial_result(res: bytes) -> dict:
    res_str = res.decode()

    match = re.match(r'^\w+: [0-9./]+$', res_str)
    if not match:
        return None

    device, readout = res_str.split(':')
    readout = readout.strip()

    values = readout.split('/')
    labels = config['SensorReadouts']
    readout_dict = {k:float(v) for k,v in zip(labels, values)}

    readout_dict['temperature_f'] = (readout_dict['temperature'] * (9/5)) + 32

    location = config['Devices'][device]['location']
    readout_dict['capacity'] = (readout_dict['person_count']  / config['Locations'][location]['capacity']) * 100

    result_dict = {
        'device': device,
        'time_completed': datetime.datetime.now().strftime(config['DateString']),
        'readout': readout_dict
    }

    return result_dict

def result_to_telegram(results: list) -> str:
    output_str = ''

    current_tz = pytz.timezone(config['TimeZone'])
    current_dt = datetime.datetime.now(current_tz)
    formatted_time = current_dt.strftime("%I:%M%p").casefold()
    formatted_tz  = current_dt.strftime("%Z")

    header_str = f'Room Conditions as of {formatted_time} {formatted_tz}:\n\n'
    header_str = header_str.replace(' 0', ' ')


    output_str += header_str

    for result in results:
        result: dict

        result_str = ''

        device = result['device']
        device_info = config['Devices'].get(device)
        if not device_info:
            print(f"Log here that there's a device not configured {device}")
            continue

        location = device_info['location']
        location_info = config['Locations'].get(location)
        if not location_info:
            print(f"Log here that the location does not exist {location}")
            continue

        location_alias = location_info.get('alias', '???')
        result_header = f"{location_alias}:\n"

        result_str += result_header

        readouts = result['readout']
        read_outputs = config['Output']
        for reading in read_outputs:
            reading_info = config['Readouts'].get(reading)
            if not reading_info:
                print(f"Log here that the readout does not exist {reading_info}")

            value = readouts.get(reading, 0)
            reading_alias = reading_info.get('alias', '???')
            reading_end = reading_info.get('ending')
            reading_prec = reading_info.get('precision', 0)

            readout_str = f"{reading_alias}: {value:.{reading_prec}f}"
            readout_str += f"{reading_end}\n" if reading_end else "\n"

            result_str += readout_str

        result_str += '\n'
        output_str += result_str

    return output_str[:-2]

def setup_serial(port: str = None,
                 baud: int = 38400,
                 bits:int = serial.EIGHTBITS,
                 stop_bits:int = serial.STOPBITS_ONE,
                 parity: str = serial.PARITY_NONE,
                 xonxoff:bool = True,
                 timeout:int = 900) -> serial.Serial:

    ser = serial.Serial(port=port,
                        baudrate=baud,
                        bytesize=bits,
                        stopbits=stop_bits,
                        parity=parity,
                        xonxoff=xonxoff,
                        timeout=timeout)

    return ser

def list_ports() -> list:
    # https://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python
    ports = serial.tools.list_ports.comports()
    return ["{}: {} [{}]".format(port, desc, hwid) for port, desc, hwid in sorted(ports)]

if __name__ == "__main__":
    load_dotenv(file_path / '.env')

    port = os.environ.get('PORT')
    if not port:
        print('Please specify a port from the possible options:')
        for port in list_ports():
            print(f'-  {port}')
        quit()

    serial_info = port
    bot_info = os.environ.get('TELEGRAM_KEY')

    main(serial_info, bot_info)

