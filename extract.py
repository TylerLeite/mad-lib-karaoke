from enum import Enum, IntEnum
import re
import json

from db import DB
from hyphenate import hyphenate_word

from MIDI import MIDIFile, Events

class KarTag(str, Enum):
    TagIdentifier = "@"
    FiletypeCopyright = "K"
    Language = "L"
    TitleArtistSequencer = "T"
    OtherInformation = "I"

class KarCommand(str, Enum):
    ClearScreen = '\\'
    NewLine = '/'
    NewWord = ' '
    UnknownCommand = '?'
    NoCommand = ''

class MetaType(IntEnum):
    Text = 1
    Lyric = 5

ATTR_ALLOWED = "1234567890qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM-_"
def attr_code(text):
    safe = ""
    for c in text.lower():
        if c not in ATTR_ALLOWED:
            safe += '_'
        else:
            safe += c
    return safe

class Word:
    # word is a fucked up word if you keep typing it enough
    def __init__(self, meta_type, events, track_idx, event_idxs, word_in_event_idxs):
        self.meta_type = meta_type
        self.events = events
        self.track_idx = track_idx
        self.event_idxs = event_idxs
        self.word_idxs = word_in_event_idxs

        self.texts = []
        self._generate_texts()

        self.is_last_in_line = False

        if self.meta_type == MetaType.Text:
            try:
                self.command = KarCommand(self.texts[0][0])
            except:
                self.command = KarCommand.UnknownCommand
            
            combined_text = re.sub(r"[\\\/ ]", '', "".join(self.texts))

            if len(combined_text) == 0:
                self.prenctuation = ""
                self.punctuation = ""
                self.word = ""
                self.n_syllables = 0
                self.attr = ""
                return
            else:
                self.prenctuation = ""
                if combined_text[0] == '"' or combined_text[0] == "'":
                    self.prenctuation = combined_text[0]
                    combined_text = combined_text[1:]

                split_text = [s for s in re.split(r"([a-zA-Z']+)", combined_text) if len(s) > 0]
                self.word = split_text[0]
                self.punctuation = "".join(split_text[1:])
                self.attr = attr_code(self.word)
        elif self.meta_type == MetaType.Lyric:
            self.command = KarCommand.NoCommand
            combined_text = "".join(self.texts).replace(' ', '')

            self.prenctuation = ""
            if combined_text[0] == '"' or combined_text[0] == "'":
                self.prenctuation = combined_text[0]
                combined_text = combined_text[1:]

            split_text = [s for s in re.split(r"([a-zA-Z']+)", combined_text) if len(s) > 0]
            self.punctuation = "".join(split_text[1:])
            self.word = split_text[0]

            self.attr = attr_code(self.word)
        else:
            print("Unknown meta type in word")
        
        self.n_syllables = len(hyphenate_word(self.word))

    def _generate_texts(self):
        texts = []
        for i, event in enumerate(self.events):
            text = event.data.decode('utf-8')

            if self.meta_type == MetaType.Text:
                # TODO: pretty sure i wrote this at like 4 a.m., no idea what's going on here
                parts = text.split(' ')
                parts = [parts[0]] + [' ' + part for part in parts[1:]]
                if text[0] == ' ':
                    parts = parts[1:]
                
                texts.append(parts[self.word_idxs[i]])
            elif self.meta_type == MetaType.Lyric:
                if text[0] == ' ':
                    texts.append(text[1:])
                else:
                    texts.append(text)
            else:
                print("Unknown meta type in word")

        self.texts = texts

    def __repr__(self):
        reprs = []
        if self.meta_type == MetaType.Text:
            for i, text in enumerate(self.texts):
                reprs.append(f"{self.event_idxs[i]}.{self.word_idxs[i]}: {self.texts[i]}")
            return f"@{self.track_idx}" + '{' + " | ".join(reprs) + '}'
        elif self.meta_type == MetaType.Lyric:
            for i, text in enumerate(self.texts):
                reprs.append(f"{self.event_idxs[i]}.{self.texts[i]}")
            return f"@{self.track_idx}" + '{' + " | ".join(reprs) + '}'
        else:
            return "<WORD WITH UNKNOWN META TYPE>"

def generate_word_dict(midi):
    word_dict = {}
    words = []

    for i, track in enumerate(midi):
        track.parse()

        word_events = []
        word_event_jndices = []
        word_event_kndices = []
        for j, event in enumerate(track):
            if isinstance(event, Events.MetaEvent):
                if event.type not in (MetaType.Text, MetaType.Lyric):
                    # Ignore all events that don't contain text
                    continue

                text = event.data.decode('utf-8')
                if len(text) == 0:
                    continue
                    
                if event.type == MetaType.Text:
                    # Metadata, ignore
                    if text[0] == KarTag.TagIdentifier:
                        continue
                    else:
                        # Each syllable gets its own event, may need to combine multiple events into 1 word
                        # But also a single event might contain multiple words

                        # In this case, the event contains multiple words
                        words_in_event = []
                        words_in_event = text.split(' ')
                        words_in_event = [words_in_event[0]] + [' ' + part for part in words_in_event[1:]]
                        if text[0] == ' ':
                            words_in_event = words_in_event[1:]

                        for k, _text in enumerate(words_in_event):
                            # This should always be the case except when processing the first event
                            if len(word_events) > 0:
                                if _text[0] not in (' ', '\\', '/'):
                                    # Continuation of word from a previous event
                                    word_events.append(event)
                                    word_event_jndices.append(j)
                                    word_event_kndices.append(k)
                                    continue
                                else:
                                    # New word, process previous one
                                    w = Word(MetaType.Text, word_events, i, word_event_jndices, word_event_kndices)
                                    words.append(w)
                                    if w.attr not in word_dict:
                                        word_dict[w.attr] = []
                                    word_dict[w.attr].append(w)
                            
                            # Beginning of a new word    
                            word_events = [event]
                            word_event_jndices = [j]
                            word_event_kndices = [k]
                elif event.type == MetaType.Lyric:
                    word_events.append(event)
                    word_event_jndices.append(j)
                    # Lyrics are interpreted differently
                    # A standalone event with data = 0x0D ('\r') denotes a new line
                    # Spaces are at the end of the word rather than the beginning of the next one
                    # Words can still be split over multiple events, it seems like each event can only have one word in it
                    
                    if text[-1] == ' ' or event.data == b'\r':
                        w = Word(MetaType.Lyric, word_events, i, word_event_jndices, [0])
                        if event.data == b'\r':
                            w.is_last_in_line = True
                            
                        words.append(w)
                        if w.attr not in word_dict:
                            word_dict[w.attr] = []
                        word_dict[w.attr].append(w)

                        # reset for the next word
                        word_events = []
                        word_event_jndices = []

        # Get the last word left over (only necessary for text-type meta events)
        if len(word_events) > 0:
            w = Word(MetaType.Text, word_events, i, word_event_jndices, word_event_kndices)
            words.append(w)
            if w.word.lower() not in word_dict:
                word_dict[w.attr] = []
            word_dict[w.attr].append(w)

    return word_dict, words

def format_words(words):
    lyrics = []
    line = []

    for word in words:
        if word.texts[0][0] in ('/', '\\'):
            if len(line) > 0:
                lyrics.append(line)
                line = []
        line.append(word)
        if word.is_last_in_line:
            lyrics.append(line)
            line = []
    lyrics.append(line)

    return lyrics

def by_id(id):
    # TODO: pass filen instead of song id
    for song in DB["songs"]:
        if song["id"] == id:
            filen = DB["config"]["karaoke_dir"] + song["filen"]

            midi = MIDIFile(filen)
            midi.parse()
            word_dict, words = generate_word_dict(midi)

            return {
                "words": format_words(words),
                "word_dict": word_dict,
            }
        else:
            continue

class WordReplacement:
    def __init__(self, word, new_text):
        self.word = word
        self.new_text = new_text

    def __lt__(self, other):
        if self.word.track_idx == other.word.track_idx:
            return self.word.event_idxs[0] < other.word.event_idxs[0]
        else:
            return self.word.track_idx < other.word.track_idx

def replace_in_title(key, replaceWith, title):
    new_title = []
    for word in title:
        attr = attr_code(word)
        if attr == key:
            new_title.append(replaceWith.title())
        else:
            new_title.append(word)
    return new_title

def construct_madlib_file(ofd, midi_filen, madlib):
    midi = MIDIFile(midi_filen)
    midi.parse()
    word_dict, _ = generate_word_dict(midi)

    replacements = []
    out_title_words = ofd["title"].split(' ')
    for m in madlib:
        key = m["baseWordKey"]
        new_text = m["replaceWith"]

        words = word_dict[key]
        for word in words:
            replacements.append(WordReplacement(word, new_text))
            out_title_words = replace_in_title(key, new_text, out_title_words)
    
    # sort replacements such that highest event_idx[0] is at the front
    replacements = sorted(replacements, reverse=True)

    in_words = []
    new_texts = []
    for replacement in replacements:
        in_words.append(replacement.word)
        new_texts.append(replacement.new_text)

    for i in range(len(in_words)):
        replace_one_word(midi, in_words[i], new_texts[i])


    # ofd = out_filen_data
    ofd["title"] = "_".join(out_title_words)
    out_filen = f"{ofd['title']}_sung_by_{ofd['singer']}_filled_by_{ofd['author']}__{ofd['id']}.kar"

    midi.export(ofd["dir"] + out_filen)
    

# tide goes in, tide goes out. can't explain it
# note: replace from the back to front so you don't mess up ev_indices
def replace_one_word(midi, in_word, new_text):
    # 1. calculate time for all events combined
    start_time = in_word.events[0].time
    total_delta = 0
    for ev in in_word.events:
        total_delta += ev.delta

    # 2. identify events to replace
    track = midi.tracks[in_word.track_idx]

    # TODO: support non-contiguous events?
    # TODO: support removing a word part from an event if that event has the end of one word and the beginning of another?
    id_0 = in_word.event_idxs[0]
    id_f = in_word.event_idxs[-1]
    
    # 3. create new events for each syllable in new_word
    syllables = hyphenate_word(new_text)
    N = len(syllables)
    deltas = [total_delta // N + (1 if n < total_delta % N else 0) for n in range(N)]
    new_events = []

    if (in_word.meta_type == MetaType.Text) and (in_word.command != KarCommand.UnknownCommand):
        syllables[0] = in_word.command + syllables[0]
    if in_word.meta_type == MetaType.Lyric:
        syllables[-1] = syllables[-1] + ' '
    for i, s in enumerate(syllables):
        # buffer looks like [0xff 0x01 <length> <syllable>]
        buf = bytearray([0xff])
        if in_word.meta_type == MetaType.Text:
            buf.extend(bytearray([0x01]))
        elif in_word.meta_type == MetaType.Lyric:
            buf.extend(bytearray([0x05]))
        else:
            print("Unknown meta type when replacing word")
            break

        buf.extend(len(s).to_bytes(1, "big")) # length will never be > 127
        buf.extend(s.encode("utf-8"))
        
        ev = Events.MetaEvent(deltas[i], start_time, buf)
        new_events.append(ev)
        start_time += deltas[i]

    # 4. the ol' switcheroo
    track.events[id_0:id_f+1] = new_events