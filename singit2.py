#!/usr/bin/python

from os import system
import sys,time,math,string,subprocess,copy
import mido

transpose = 0 + 12
min_duration = 250
max_duration = 30000
#voice = 'Zarvox'
#voice = 'Fred'
#voice = 'Bruce'
#voice = 'Kathy'
#voice = 'Princess'

#voice = 'Alex'
#voice = 'Agnes'
voice = 'Vicki'
#voice = 'Victoria'

outcount = 0
output_file = ''
#output_file = '/Users/sehugg/midi/test%d.aiff'

LYRIC_TYPES = ['lyrics', 'text']
VOCAL_TRACK_NAMES = ['melody', 'lead vocal', 'lead', 'vocal', 'vocals', 'main  melody track',
    'bonnie tyler singing', 'melody/vibraphone', 'vocal1']
pitch_correct = 0.85
tuning_correct = 0.2
melody_track_idx = -2

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
        if len(l) and l[0]!='{' and l[0]!='.' and l[0]!='_' and l[0]!='~':
            result.append(l)
            #print l
            dur = int(l.split()[2][:-1])
            totaldur += dur
    r = (totaldur,result)
    phoneme_cache[text] = copy.deepcopy(r)
    return r

tuning_error = 0

def fix_phonemes(phonlist, newdur, freq):
    global tuning_error
    olddur = phonlist[0]
    newlist = []
    for l in phonlist[1]:
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
            newlist.append(string.join(toks,' '))
    phonlist[1][:] = newlist

#with stopping current speech without waiting until completion

def sing_track(track, channels=None, msgs=None, type=None):
    s = '[[inpt TUNE]]\n'
    phrase = ''
    t = 0
    note_t0 = 0
    note = 0
    totaldur = 0
    curfreq = 20
    for msg in track:
        t += msg.time
        #print msg.time,msg,phrase
        tms = int(t*1000)
        if channels and hasattr(msg,'channel') and not msg.channel in channels:
            continue
        if msgs and not msg in msgs:
            continue
        #print t,tms-note_t0,note,phrase,msg
        if msg.is_meta and msg.type == type:
            phrase += msg.text
        if msg.type == 'note_on' and msg.velocity > 0:
            dur = tms-note_t0
            note = msg.note + transpose
            if dur > min_duration:
                note_t0 += dur
                totaldur += dur
                if output_file=='':
                    dur = min(dur,1000)
                s += '%% {D %d}\n' % dur
        elif msg.type in ['note_on','note_off'] and note and tms > note_t0 and phrase.strip() != '':
            duration = max(min_duration, tms-note_t0)
            freq = 440.0 / 10.0 * math.pow(2.0, (note - 49) / 12.0);
            phonlist = get_phoneme_list(phrase)
            print phrase,'\t',note,duration,len(phonlist),round(tuning_error)
            fix_phonemes(phonlist, duration, freq)
            for l in phonlist[1]:
                s += l + '\n'
            phrase = ''
            note_t0 += duration
            totaldur += duration
            note = 0
    print s
    print note_t0,totaldur
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
                print "Singing track %d channel %d, %s" % (sing_track_idx, sing_channel, sing_type)
                sing_track(mid, type=sing_type, channels=[sing_channel])
    except:
        print sys.exc_info()
        

#print "*** Sing track", sing_track, "channel", sing_channel

