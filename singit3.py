#!/usr/bin/python

from os import system
import sys,time,math,string,subprocess,copy
import mido

transpose = 0 + 12
min_duration = 250
max_duration = 30000
pause_duration = 200
#voice = 'Zarvox'
voice = 'Fred'
#voice = 'Bruce'
#voice = 'Kathy'
#voice = 'Princess'

#voice = 'Alex'
#voice = 'Agnes'
#voice = 'Vicki'
#voice = 'Victoria'

outcount = 0
output_file = ''
#output_file = '/Users/sehugg/midi/test%d.aiff'

LYRIC_TYPES = ['lyrics', 'text']
VOCAL_TRACK_NAMES = ['melody', 'lead vocal', 'lead', 'vocal', 'vocals', 'main  melody track',
    'bonnie tyler singing', 'melody/vibraphone', 'vocal1']
pitch_correct = 0.95
tuning_correct = 0.20
melody_track_idx = -2
fixspaces = 0

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

phoneme_cache = {}

def get_phoneme_list(text):
    r = phoneme_cache.get(text)
    if r:
        return copy.deepcopy(r)
    cmd = ['./phonemes','-v',voice,'-t',text]
    response = subprocess.check_output(cmd)
    lines = response.split('\n')
    result = []
    totaldur = 0
    for l in lines:
        if len(l):
            result.append(l)
            if l.find(' P ')>=0:
                dur = int(l.split()[2][:-1])
                totaldur += dur
    r = (totaldur,result)
    phoneme_cache[text] = copy.deepcopy(r)
    return r

tuning_error = 0

def fix_phoneme(l, olddur, newdur, freq):
    global tuning_error
    toks = l.split()
    dur0 = int(toks[2][:-1])
    dur1 = int(round(dur0*newdur/olddur))
    dur1 = min(max_duration, dur1)
    toks[2] = str(dur1) + toks[2][-1]
    for i in range(3,len(toks)):
        if toks[i].find(':')>0:
            f1,p1 = toks[i].split(':')
            f1 = float(f1)
            f2 = freq*pitch_correct + f1*(1-pitch_correct)
            f2 -= tuning_error * tuning_correct
            fdiff = (f2-freq)
            tuning_error += fdiff
            #f2 = freq + (f1-avgf)/4
            toks[i] = str(f2) + ':' + p1
    if dur1>=5:
        return (dur0, dur1, string.join(toks,' '))
    else:
        return (dur0, 0, None)

class Phrase:
    def __init__(self):
        self.text = ''
        self.notes = []
    def __repr__(self):
        return '"%s"%s' % (self.text, self.notes)

def split_phrases(track, channels=None, type=None):
    note_start = 0
    note_end = 0
    note = 0
    t = 0
    cur_phrase = Phrase()
    phrases = []
    for msg in track:
        t += msg.time
        tms = int(t*1000)
        if channels and hasattr(msg,'channel') and not msg.channel in channels:
            continue
        if msg.is_meta and msg.type == type and len(msg.text):
            cur_phrase.text += msg.text
            if fixspaces and msg.text[-1] != '-':
                cur_phrase.text += ' '
        if msg.type == 'note_on' and msg.velocity > 0:
            if not note and tms > note_end + pause_duration:
                if len(cur_phrase.notes):
                    phrases.append(cur_phrase)
                    cur_phrase = Phrase()
            note = msg.note
            note_start = tms
        elif msg.type in ['note_on','note_off']:
            if note == msg.note:
                cur_phrase.notes.append((note,note_start,tms,len(cur_phrase.text)))
                note_end = tms
                note = 0
    if len(cur_phrase.notes):
        phrases.append(cur_phrase)
    return phrases

def sing_phrase(p):
    print p
    phons = get_phoneme_list(p.text)
    text = p.text.upper()
    ttsdur = phons[0]
    ttslist = phons[1]
    newlist = []
    newdur = p.notes[-1][2] - p.notes[0][1]
    print ttsdur,newdur
    notetime = p.notes[0][1]
    note_idx = 0
    for i in range(0,len(ttslist)):
        ph = phons[1][i]
        print ph
        if ph[0] == '_' or ph[0] == '~':
            word = ph.split('"')[1]
        elif ph.find(' P ') >= 0:
            if notetime >= p.notes[note_idx][2]:
                note_idx += 1
            note = p.notes[note_idx][0] + transpose
            freq = 440.0 / 10.0 * math.pow(2.0, (note - 49) / 12.0);
            dur0,dur1,newph = fix_phoneme(ph, ttsdur, newdur, freq)
            if newph:
                newlist.append(newph)
            notetime += dur1
    return notetime, string.join(newlist, '\n')

def sing_track(track, channels=None, type=None):
    phrases = split_phrases(track, channels, type)
    s = '[[inpt TUNE]]\n'
    t = 0
    for p in phrases:
        tend = p.notes[-1][2]
        tstart = p.notes[0][1]
        if tstart > t and output_file != '':
            s += '%% {D %d}\n' % (tstart - t)
        t,l = sing_phrase(p)
        s += l
    say(s)

###

for fn in sys.argv[1:]:
    print "======================================================"
    print fn
    try:
        mid = mido.MidiFile(fn)
        print mid
        sing_type = 'lyrics'
        for i, track in enumerate(mid.tracks):
            sing_track_idx = -1
            sing_channel = -1
            print('Track {}: {}'.format(i, track.name))
            for msg in track:
                if msg.is_meta and msg.type in LYRIC_TYPES and len(msg.text)>2:
                    sing_track_idx = i
                    sing_type = msg.type
                if msg.type == 'note_on' and (i == sing_track_idx 
                    or i == melody_track_idx
                    or track.name.strip().lower() in VOCAL_TRACK_NAMES):
                    sing_channel = msg.channel
            if sing_channel >= 0:
                print "Singing track %d channel %d, %s" % (sing_track_idx, sing_channel, sing_type)
                sing_track(mid, type=sing_type, channels=[sing_channel])
    except:
        print sys.exc_info()
        

#print "*** Sing track", sing_track, "channel", sing_channel

