import os, pathlib, json, shutil

file_path = pathlib.Path(__file__).parent.resolve()

with open(file_path/'config.json', encoding='utf-8') as json_file:
    config = json.load(json_file)

logfile = file_path/'furflow.log'

print(os.path.isfile(logfile))
