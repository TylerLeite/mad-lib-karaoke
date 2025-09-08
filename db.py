import os
import json
from uuid import uuid4 as uuid
from base64 import b16encode

DB = {}

def initdb(CFG):
    DB["config"] = CFG
    with open(DB["config"]["song_index"], "rb") as json_file:
        DB["songs"] = json.load(json_file)

def get_template_str(song_id):
    template_filen = f'{DB["config"]["madlib_template_dir"]}{song_id}.json'
    out = "{}"
    try:
        with open(template_filen, 'r') as template_file:
            out = template_file.read()
    except FileNotFoundError:
        pass # nbd just return "{}"
    return out

def write_template(song_id, new_json):
    template_filen = f'{DB["config"]["madlib_template_dir"]}{song_id}.json'
    with open(template_filen, 'w') as template_file:
        json.dump(new_json, template_file)

def get_template(song_id):
    template_str = get_template_str(song_id)
    return json.loads(template_str)

def get_config():
    return DB["config"]

def get_song(id):
    return get_songs()[int(id)]

def get_songs():
    return DB["songs"]

def get_madlibs():
    madlib_dir = f'{DB["config"]["filled_madlib_dir"]}'
    madlibs_filens = [
        os.path.join(madlib_dir, f) for f in os.listdir(madlib_dir) if 
            os.path.isfile(os.path.join(madlib_dir, f)) 
            and os.path.splitext(f)[-1] == '.json'
    ]

    madlibs = []
    for filen in madlibs_filens:
        with open(filen) as file:
            madlibs.append(json.load(file))
    return madlibs

def madlib_create(song_id):
    madlib_id = b16encode(uuid().bytes).decode("ascii").lower()
    template = get_template(song_id)

    fillings = []
    for word in template["selectedWords"]:
        fillings.append({
            "baseWordKey": word["baseWordKey"],
            "prompt": word["prompt"],
            "replaceWith": "",
        })

    madlib_entry = {
        "id": madlib_id,
        "song": song_id,
        "song_name": get_songs()[int(song_id)]["title"],
        "singer_name": "",
        "author_name": "",
        "fillings": fillings,
    }

    madlib_filen = f'{DB["config"]["filled_madlib_dir"]}{madlib_id}.json'
    with open(madlib_filen, 'w') as madlib_file:
        json.dump(madlib_entry, madlib_file)
    
    return madlib_id

def madlib_edit(madlib_id, madlib):
    madlib_filen = f'{DB["config"]["filled_madlib_dir"]}{madlib_id}.json'
    with open(madlib_filen, 'w') as madlib_file:
        json.dump(madlib, madlib_file)

def get_madlib_str(id):
    madlib_filen = f'{DB["config"]["filled_madlib_dir"]}{id}.json'
    out = "{}"
    try:
        with open(madlib_filen, 'r') as madlib_file:
            out = madlib_file.read()
    except FileNotFoundError:
        pass # nbd just return "{}"
    return out

def get_madlib(id):
    madlib_str = get_madlib_str(id)
    return json.loads(madlib_str)

