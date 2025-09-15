import json
from flask import Flask, render_template, redirect, request

import db
import extract

CFG = {}
with open("res/config.json", "rb") as cfg_file:
    CFG = json.load(cfg_file)

db.initdb(CFG)

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/config")
def config():
    return render_template("songlist.html", mode="config", songs=db.get_all_songs())

@app.route("/config/<song>", methods=["GET", "POST"])
def config_song(song):
    if request.method == "POST":
        db.write_template(song, request.get_json())
        return { "status": 200 }
    elif request.method == "GET":
        # TODO: pass filen rather than song id
        words, word_dict = extract.by_id(song).values()
        existing_config = db.get_template_str(song)
        return render_template("config.html", existing_config=existing_config, lyrics=words)

@app.route("/madlibs")
def madliblist():
    return render_template("madliblist.html", madlibs=db.get_madlibs())

@app.route("/madlib")
def songlist():
    return render_template("songlist.html", mode="madlib", songs=db.get_songs_with_templates())

@app.route("/madlib/<song>")
def madlib(song):
    id = db.madlib_create(song)
    return redirect(f"/madlib/edit/{id}")

@app.route("/madlib/edit/<id>", methods=["GET", "POST"])
def madlib_edit(id):
    if request.method == "POST":
        db.madlib_edit(id, request.get_json())
        return { "status": 200 }
    elif request.method == "GET":
        madlib_str = db.get_madlib_str(id)
        madlib = db.get_madlib(id)
        return render_template("edit.html", madlib=madlib, madlib_str=madlib_str)

@app.route("/export/<id>", methods=["POST"])
def export(id):
    if request.method != "POST":
        return { "status": 404 }

    madlib = db.get_madlib(id)

    song = db.get_song(madlib["song"])
    midi_filen = db.get_config()["karaoke_dir"] + song["filen"]

    out_filen_data = {
        "dir": db.get_config()["madlib_dir"],
        "title": song["title"],
        "singer": madlib["singer_name"],
        "author": madlib["author_name"],
        "id": madlib["id"],
    }    

    extract.construct_madlib_file(out_filen_data, midi_filen, madlib["fillings"])

    return { "status": 200 }


@app.route("/admin")
def admin():
    return f"manage queue, see all madlibs"