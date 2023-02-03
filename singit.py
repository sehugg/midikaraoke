#!/usr/bin/python

from os import system
import os,sys,time,math,argparse
import mido
import osascript

parser = argparse.ArgumentParser()
parser.add_argument('-o', '--output', action="store_true", help="output .aiff files")
parser.add_argument('-v', '--voice', default="Alex", help="system voice name")
#parser.add_argument('-m', '--melody', type=int, default=-1, help="track # of melody")
parser.add_argument('-T', '--transpose', type=int, default=0, help="transpose by half-steps")
parser.add_argument('-R', '--wordrate', type=float, default=150.0, help="speaking rate (words per second)")
parser.add_argument('midifile', help="MIDI file")
args = parser.parse_args()

LYRIC_TYPES = ['lyrics', 'text']
VOCAL_TRACK_NAMES = ['melody', 'lead vocal', 'lead', 'vocal', 'vocals', 'main  melody track',
    'voice',
    'bonnie tyler singing', 'melody/vibraphone', 'vocal1']
melody_track_idx = -2

transpose = args.transpose
master_rate = args.wordrate
voice = args.voice

outcount = 0
output_file = ''
if args.output:
    output_file = os.getcwd() + '/test_%d.aiff'

def say(text):
    global outcount
    text = text.replace('"','')
    cmd = """say "%s" using "%s" modulation 0""" % (text, voice)
    if output_file != '':
        cmd = """say "%s" using "%s" modulation 0 saving to "%s" """ % (text, voice, output_file%outcount)
    code,response,err = osascript.run(cmd)
    if err:
        raise Error(err)
    outcount += 1

def say_old(text):
    global outcount
    text = text.replace('"','')
    cmd = """osascript<<END
say "%s" using "%s" modulation 0 
END""" % (text, voice)
    if output_file != '':
        cmd = """osascript<<END
say "%s" using "%s" modulation 0 saving to "%s"
END""" % (text, voice, output_file%outcount)
    response = str(system(cmd))
    outcount += 1
    print(response)
    if response == "good":
        print("Ok")

#with stopping current speech without waiting until completion

def sing_track(track, channels=None, msgs=None, type=None):
    s = ''
    phrase = ''
    t = 0
    note_t0 = 0
    note = 60
    for msg in track:
        t += msg.time
        #t += mido.tick2second(msg.time, 96, 700000) # TODO
        if channels and hasattr(msg,'channel') and not msg.channel in channels:
            continue
        if msgs and not msg in msgs:
            continue
        #print(t,msg)
        if msg.type == 'note_on' and msg.velocity > 0:
                #if output_file!='' and (t-note_t0) > 0:
                #    s += '[[slnc %d]]' % (1000*(t-note_t0))
                note = msg.note + transpose
                note_t0 = t
        elif msg.type in ['note_on','note_off'] and note and t > note_t0 and phrase.strip() != '':
                rate = int(master_rate / (t-note_t0))
                rate = master_rate
                #freq = 440.0 * math.pow(2.0, (note - 69) / 12.0);
                s += '[[pbas %f; pmod 1; rate %d]]%s' % (note, rate, phrase)
                phrase = ''
                note_t0 = t
                #say(msg.text, note)
        if msg.is_meta and msg.type == type:
                phrase += msg.text
    print(s)
    say(s)

###

for fn in [args.midifile]:
    print("======================================================")
    print(fn)
    mid = mido.MidiFile(fn)
    sing_type = 'lyrics'
    for i, track in enumerate(mid.tracks):
        sing_track_idx = -1
        sing_channel = -1
        print(('Track {}: {}'.format(i, track.name)))
        track_msgs = []
        for msg in track:
            track_msgs.append(msg)
            if msg.is_meta and msg.type in LYRIC_TYPES and len(msg.text)>2:
                sing_track_idx = i
                sing_type = msg.type
            if msg.type == 'note_on' and (i == sing_track_idx 
                or i == melody_track_idx
                or track.name.strip().lower() in VOCAL_TRACK_NAMES):
                sing_channel = msg.channel
        if sing_channel >= 0:
            print("Singing track %d channel %d, %s" % (sing_track_idx, sing_channel, sing_type))
            sing_track(mid, type=sing_type, channels=[sing_channel])

#print "*** Sing track", sing_track, "channel", sing_channel

