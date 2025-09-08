#!/bin/sh
python3 -m pip venv .env
source .env/bin/activate
pip install -r requirements.txt
echo "You will still need to find or create .kar files and place them in res/midi/karaoke-files"
echo "You will then need to create a res/song_index.json file"