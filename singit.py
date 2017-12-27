#!/usr/bin/python

from os import system
import os,sys,time,math,argparse
import mido

parser = argparse.ArgumentParser()
parser.add_argument('-o', '--output', action="store_true", help="output .aiff files")
parser.add_argument('-v', '--voice', default="Alex", help="system voice name")
#parser.add_argument('-m', '--melody', type=int, default=-1, help="track # of melody")
parser.add_argument('-T', '--transpose', type=int, default=-12, help="transpose by half-steps")
parser.add_argument('-R', '--wordrate', type=float, default=100.0, help="speaking rate (words per second)")
parser.add_argument('midifile', help="MIDI file")
args = parser.parse_args()

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
    cmd = """osascript<<END
say "%s" using "%s" modulation 0 
END""" % (text, voice)
    if output_file != '':
        cmd = """osascript<<END
say "%s" using "%s" modulation 0 saving to "%s"
END""" % (text, voice, output_file%outcount)
    response = str(system(cmd))
    outcount += 1
    print response
    if response == "good":
        print "Ok"

#with stopping current speech without waiting until completion

def sing_track(track):
    s = ''
    phrase = ''
    t = 0
    note_t0 = 0
    note = 60
    for msg in track:
        t += mido.tick2second(msg.time, 96, 700000) # TODO
        #print t,msg
        if msg.type == 'note_on' and msg.velocity > 0:
                #if output_file!='' and (t-note_t0) > 0:
                #    s += '[[slnc %d]]' % (1000*(t-note_t0))
                note = msg.note + transpose
                note_t0 = t
        if msg.is_meta and msg.type in ['text','lyrics']:
                phrase += msg.text
        if msg.type == 'note_on' and msg.velocity == 0 and t > note_t0:
                rate = int(master_rate / (t-note_t0))
                freq = 440.0 * math.pow(2.0, (note - 69) / 12.0);
                s += '[[pbas %f; pmod 0; rate %d]]%s' % (freq, rate, phrase)
                phrase = ''
                note_t0 = t
                #say(msg.text, note)
    print s
    say(s)

###

for fn in [args.midifile]:
    print "======================================================"
    print fn
    try:
        mid = mido.MidiFile(fn)
        print mid
        sing_track_idx = 0
        for i, track in enumerate(mid.tracks):
            print('Track {}: {}'.format(i, track.name))
            for msg in track:
                #print msg
                if msg.is_meta and msg.type in ['text', 'lyrics']:
                    sing_track_idx = i
                    sing_track(track)
                    break
                if i == sing_track and msg.type == 'note_on':
                    sing_channel = msg.channel
    except:
        print sys.exc_info()

#print "*** Sing track", sing_track, "channel", sing_channel

