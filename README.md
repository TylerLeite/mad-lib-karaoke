# Mad Lib Karaoke

* install with `./install.sh`
* find .kar files or make them yourself and `mv *.kar res/midi/karaoke-files/`
* `touch res/song_index.json` and then fill it out according to this template

```
[{
    "id": "0",
    "title": "<song title>",
    "artist": "<song artist>",
    "filen": "<song filename (not including directory)>"
}, {
    ...
}]
```