#!/usr/bin/python

from os import system
import sys,os,time,math,string,subprocess,copy,codecs,aifc,re
import argparse
import mido

parser = argparse.ArgumentParser()
parser.add_argument('-o', '--output', action="store_true", help="output .aiff files")
parser.add_argument('-v', '--voice', default="Alex", help="system voice name")
parser.add_argument('-m', '--melody', type=int, default=-2, help="track # of melody")
parser.add_argument('-T', '--transpose', type=int, default=-12, help="transpose by half-steps")
parser.add_argument('-P', '--pauseduration', type=int, default=200, help="pause duration in msec")
parser.add_argument('-H', '--harmonyindex', type=int, default=0, help="harmony index")
parser.add_argument('-X', '--purgewords', action="store_true", help="purge lyrics before phrase")
parser.add_argument('-c', '--cps', type=int, default=25, help="max chars per sec")
parser.add_argument('midifile', help="MIDI file")
parser.add_argument('midichannels', nargs='?', help="comma-separated list of MIDI channels, or -")
args = parser.parse_args()

transpose = args.transpose
max_duration = 30000
pause_duration = args.pauseduration
voice = args.voice

#voice = 'Zarvox'
#voice = 'Fred'
#voice = 'Bruce'
#voice = 'Kathy'
#voice = 'Princess'
#voice = 'Alex'
#voice = 'Agnes'
#voice = 'Vicki'
#voice = 'Victoria'

outcount = 0
output_file = ''
if args.output: # TODO
    output_file = '/Users/sehugg/midi/test_%d_%d.aiff'
harmony_index = args.harmonyindex

LYRIC_TYPES = ['lyrics', 'text']
VOCAL_TRACK_NAMES = ['melody', 'lead vocal', 'lead', 'vocal', 'vocals', 'vocal\'s', 'voice', 'chorus',
    'main  melody track', 'second melody track', 'guide melody', 'background melody',
    'vocal 1', 'vocal 2', 'vocals 1', 'vocals 2', 'bkup vocals', 'backup singers', 'background vocals',
    'eric ernewein',
    'organ 3', 'lead organ', 'lead organ 3', 'harm 1 organ 3', 'harm 2 organ 3', 'harm 3 organ 3', 'rock organ lead',
    'bonnie tyler singing', 'melody/vibraphone', 'vocal1', 'solovox']
pitch_correct = 0.92
tuning_correct = 0.20
melody_track_idx = args.melody
fixspaces = 0
fixslashes = 0
max_char_per_sec = args.cps
fix_durations = 1
purge_words = args.purgewords

lyric_substitutions = [
('You say ', 'Colton '),
('It\'s my birthday too', 'You\'re nine years old'),
('I would like you to ', 'Kitty and Daisy will '),
('Peach', 'Birthday'),
('peach', 'birthday'),
('holiday', 'birthday'),
('Holiday', 'Birthday'),
('nowhere', 'birthday'),
('Nowhere', 'Birthday'),
('of the tiger', 'of Colton\'s birthday'),
('Ziggy', 'Colton'),
('Weird', 'Becca'),
('Gilly', 'Kay-lyn'),
('hung', 'groomed'),
('balls', 'butts'),
('bitched', 'kvetched'),
('SOS', 'birthday wish'),
('Message in a bottle','Happy Birthday Cohlton'),
('Shattered','Birthday'),
('shattered','birthday'),
]
lyric_substitutions = []

###

def fix_aiff_timing(text, srcfn):
    print "Fixing",srcfn
    newfn = srcfn+'.tmp'
    af = aifc.open(srcfn,'rb')
    time2samp = af.getframerate()/1000.0
    t = 0
    gaps = []
    mingap = pause_duration
    s = ''
    for l in text.split('\n'):
        if l.find('{D ')>0:
            toks = l.split()
            dur0 = int(toks[2][:-1])
            mingap = min(mingap, dur0)
            s += toks[0]
            if l.find(' P ')<0:
                t0 = int(t*time2samp)
                t1 = int((t+dur0)*time2samp)
                if len(gaps) and t0 == gaps[-1][1]:
                    gaps[-1] = ((gaps[-1][0],t1,s)) # append to last gap
                else:
                    gaps.append((t0,t1,s)) # create new gap
                s = ''
            t += dur0
    totaldur = t
    print gaps
    if fix_durations:
        mingap = time2samp*500
    else:
        mingap = (mingap-1)*time2samp/2
    print "Min gap",mingap,"frames"
    bs = 512 # block size
    t = 0 # time
    outdata = '' # output frames
    for gapi in range(0,len(gaps)):
        # copy silence
        gapdur = gaps[gapi][1] - t
        print t,gapdur
        if gapdur > 0:
            outdata += '\0\0' * gapdur
            t += gapdur
        # copy voice from src aiff
        sc = 0 # silence counter
        state = 0 # 0 = skip silence
        while sc < mingap: # TODO???
            data = af.readframes(bs)
            if len(data) <= 0:
                break
            for i in range(0,len(data),2):
                if data[i] == '\0' and data[i+1] == '\0':
                    if state:
                        sc += 1 # count silence frames
                else:
                    outdata += data[i:i+2] # copy data
                    state = 1
                    sc = 0
                    t += 1
    print len(outdata)/2,totaldur*time2samp
    af.close()
    newf = aifc.open(srcfn,'wb')
    newf.setnchannels(af.getnchannels())
    newf.setsampwidth(af.getsampwidth())
    newf.setframerate(af.getframerate())
    newf.setnframes(t)
    newf.writeframes(outdata)
    newf.close()

def say(text):
    global outcount
    text = text.replace('"','')
    saytext = text
    if fix_durations or output_file == '':
        saytext = re.sub(r'% {D \d+}', '% {D 1000}', saytext)
    cmd = """osascript<<END
say "%s" using "%s" modulation 0 
END""" % (saytext, voice)
    if output_file != '':
        outfn = output_file % (outcount,harmony_index)
        cmd = """osascript<<END
say "%s" using "%s" modulation 0 saving to "%s"
END""" % (saytext, voice, outfn)
    response = str(system(cmd))
    outcount += 1
    print response
    if response == "good":
        print "Ok"
    if output_file != '' and fix_durations:
        fix_aiff_timing(text, outfn)

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

def is_vowel(s):
    for v in ['A','E','I','O','U']:
        if s.find(v)>=0:
            return True
    return False

def fix_phoneme(l, olddur, newdur, freq):
    global tuning_error
    toks = l.split()
    dur0 = int(toks[2][:-1])
    dur1 = int(round(dur0*newdur/olddur))
    dur1 = min(max_duration, dur1)
    toks[2] = str(dur1) + toks[2][-1]
    #vowel = is_vowel(toks[0])
    #if vowel:
    #    dur1 = dur0
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
    def duration(self):
        return self.notes[-1][2] - self.notes[0][1]
    def CPS(self):
        return len(self.text) * 1000.0 / self.duration()

def split_phrases(track, channels=None, type=None):
    note_start = 0
    note_end = 0
    note = 0
    notes_on = set()
    t = 0
    cur_phrase = Phrase()
    phrases = []
    nexttext = ''
    for msg in track:
        t += msg.time
        tms = int(t*1000)
        if channels and hasattr(msg,'channel') and not msg.channel in channels:
            continue
        #print t,note,notes_on,msg,cur_phrase
        if msg.is_meta and msg.type == type and len(msg.text):
            text = msg.text
            if len(text) and not text[0] in ['@','%']:
                text = text.replace('/',' ').replace('\\',' ')
                if fixspaces and text[-1] != '-':
                    text += ' '
                nexttext += text
            #print text,cur_phrase
        if msg.type == 'note_on' and msg.velocity > 0:
            # flush phrase?
            if not note and tms > note_end + pause_duration:
                if len(cur_phrase.notes):
                    pos = cur_phrase.text.find(' DELAYVIBR DELAY ') # Nowhere Man
                    if pos > 0:
                        cur_phrase.text = cur_phrase.text[pos+16:]
                    for a,b in lyric_substitutions:
                        cur_phrase.text = cur_phrase.text.replace(a,b)
                    char_per_sec = cur_phrase.CPS()
                    if char_per_sec < max_char_per_sec:
                        phrases.append(cur_phrase)
                    else:
                        print "Skipped, CPS =", char_per_sec
                        print cur_phrase
                    cur_phrase = Phrase()
                    if purge_words:
                        nexttext = ''
            # replace this note?
            if note:
                cur_phrase.notes.append((note,note_start,tms,len(cur_phrase.text)))
                note_end = tms
                note = 0
            cur_phrase.text += nexttext
            nexttext = ''
            note_start = tms
            notes_on.add(msg.note)
            if harmony_index>0 and harmony_index <= len(notes_on):
                note = sorted(notes_on)[harmony_index-1]
            else:
                note = msg.note
        elif msg.type in ['note_on','note_off']: # note_on vel == 0
            if note in notes_on:
                notes_on.remove(note)
            if note == msg.note:
                cur_phrase.notes.append((note,note_start,tms,len(cur_phrase.text)))
                note_end = tms
                note = 0
    if len(cur_phrase.notes):
        phrases.append(cur_phrase)
    return phrases

def sing_phrase(notetime,p):
    print unicode(p).encode('utf-8')
    phons = get_phoneme_list(p.text)
    ttsdur = phons[0]
    ttslist = phons[1]
    newlist = []
    newdur = p.duration() 
    print ttsdur,' ms ->',newdur
    notetime = p.notes[0][1]
    note_idx = 0
    for i in range(0,len(ttslist)):
        ph = phons[1][i]
        print ph
        if ph[0] == '_' or ph[0] == '~':
            word = ph.split('"')[1]
        elif ph.find(' P ') >= 0:
            if notetime >= p.notes[note_idx][2] and note_idx < len(p.notes)-1:
                note_idx += 1
            note = p.notes[note_idx][0] + transpose
            freq = 440.0 * math.pow(2.0, (note - 69) / 12.0);
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
        dur = tstart - t
        while dur > 0:
            d = min(50000, dur)
            s += '%% {D %d}\n' % d
            dur -= d
        t,l = sing_phrase(t,p)
        s += l + '\n'
    # verify end time
    if output_file != '':
        dur = 0
        for l in s.split('\n'):
            toks = l.strip().split()
            if len(toks)>=3:
                dur += int(toks[2][:-1])
        print "Endtime:",t,dur
        assert t == dur
    # fix durations?
    print s
    say(s)

###

def is_vocal_track_name(name):
    name = name.strip().lower()
    for n in VOCAL_TRACK_NAMES:
        if name.find(n) >= 0:
            return True
    return False

def sing_midi(fn):
    print "======================================================"
    print fn
    mid = mido.MidiFile(fn)
    print mid
    sing_type = 'lyrics'
    main_channel = None
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
                or is_vocal_track_name(track.name)):
                sing_channel = msg.channel
                if not main_channel:
                    main_channel = sing_channel 
        if sing_channel >= 0:
            channels = [sing_channel]
            if args.midichannels:
                channels = [int(x) for x in string.split(args.midichannels,',')]
            print "Singing track %d channels %s, %s" % (sing_track_idx, channels, sing_type)
            sing_track(mid, type=sing_type, channels=channels)

###

sing_midi(args.midifile)
