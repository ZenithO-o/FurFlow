import asyncio
import telegram
import os
import pathlib
import serial
import datetime
import pytz
import re
import json
import logging
from multiprocessing.connection import PipeConnection
from multiprocessing import Process, Pipe
import serial.tools.list_ports
from dotenv import load_dotenv

file_path = pathlib.Path(__file__).parent.resolve()

with open(file_path/'config.json', encoding='utf-8') as json_file:
    config = json.load(json_file)

logfile = file_path/'furflow.log'



logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(filename=logfile,
                    encoding='utf-8',
                    level=logging.INFO,
                    format='%(levelname)s:%(name)s:%(process)d [%(asctime)s] %(message)s')

def main(serial_info, bot_info):
    t_pipe, s_pipe = Pipe(duplex=False)
    serial_p = Process(target=serial_loop, args=(serial_info, s_pipe))
    telegr_p = Process(target=telegram_loop, args=(bot_info, t_pipe))

    serial_p.start()
    telegr_p.start()

    serial_p.join()
    telegr_p.join()
    logging.info(f'Process ended.')

def serial_loop(serial_info, send_pipe: PipeConnection):
    serial_context = serial.Serial(**serial_info)

    devices_dict = {d:None for d in config['Devices']}

    logging.info('Serial Listener ready.')
    while True:
        res = listen_to_port(serial_context)
        if not res:
            continue

        logging.info('recieved message "%s".', res.decode().strip())
        res_dict = parse_serial_result(res)

        device = res_dict.get('device')
        devices_dict.update({device: res_dict})

        if all(devices_dict.values()):
            results = sorted(devices_dict.values(), key= lambda x: x['device'])
            send_pipe.send(results)
            devices_dict = {d:None for d in config['Devices']}

def telegram_loop(bot_info, recieve_pipe: PipeConnection):
    bot_context = telegram.Bot(bot_info['key'])
    chat_id = bot_info['chat']

    logging.info('Telegram Bot ready.')
    while True:
        answer = recieve_pipe.recv()
        message = result_to_telegram(answer)
        asyncio.run(send_updates(bot_context, chat_id, message))

async def send_updates(bot_context: telegram.Bot, chat_id:str, message: str):
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
        'time_completed': current_time(),
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
            logging.error('Device "%s" is not configured.', device)
            continue

        location = device_info['location']
        location_info = config['Locations'].get(location)
        if not location_info:
            logging.error('Location "%s" does not exist.', location)
            continue

        location_alias = location_info.get('alias', '???')
        result_header = f"{location_alias}:\n"

        result_str += result_header

        readouts = result['readout']
        read_outputs = config['Output']
        for reading in read_outputs:
            reading_info = config['Readouts'].get(reading)
            if not reading_info:
                logging.error('Readout variable "%s" does not exist.', reading)
                continue

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

def current_time() -> str:
    return datetime.datetime.now().strftime(config['DateString'])

if __name__ == "__main__":
    load_dotenv(file_path / '.env')

    serial_info = config['Serial']
    bot_info = {
        'key': os.environ.get('TELEGRAM_KEY'),
        'chat': os.environ.get('CHAT_ID')
    }

    main(serial_info, bot_info)

