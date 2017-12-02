#!/usr/bin/python

from os import system
import sys,time,math,string,subprocess
import mido

transpose = 0
min_duration = 50
#voice = 'Zarvox'
voice = 'Fred'
#voice = 'Bruce'
#voice = 'Alex'
#voice = 'Tom'
#voice = 'Allison'
#voice = 'Ava'

outcount = 0
output_file = ''
#output_file = '/Users/sehugg/midi/test%d.aiff'

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

def get_phoneme_list(text):
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
    return (totaldur,result)

def fix_phonemes(phonlist, newdur, freq):
    olddur = phonlist[0]
    newlist = []
    for l in phonlist[1]:
        toks = l.split()
        dur0 = int(toks[2][:-1])
        dur1 = dur0*newdur//olddur
        toks[2] = str(dur1) + toks[2][-1]
        for i in range(3,len(toks)):
            if toks[i].find(':')>0:
                toks[i] = str(freq) + ':' + toks[i].split(':')[-1]
        newlist.append(string.join(toks,' '))
    phonlist[1][:] = newlist

#with stopping current speech without waiting until completion

def sing_track(track, channels=None):
    s = '[[inpt TUNE]]\n'
    phrase = ''
    t = 0
    note_t0 = 0
    note = 60
    for msg in track:
        t += msg.time
        tms = int(t*1000)
        if channels and not msg.is_meta and not msg.channel in channels:
            continue
        #print t,tms,msg
        if msg.type == 'note_on' and msg.velocity > 0:
                dur = tms-note_t0
                if output_file=='':
                    dur = min(dur,1000)
                note = msg.note + transpose
                if dur > min_duration:
                    s += '%% {D %d}\n' % dur
                    note_t0 = tms
        if msg.is_meta and msg.type in ['text','lyrics']:
                phrase += msg.text
        if msg.type == 'note_on' and msg.velocity == 0 and tms > note_t0:
                duration = (tms-note_t0)
                freq = 440.0 / 10.0 * math.pow(2.0, (note - 49) / 12.0);
                phonlist = get_phoneme_list(phrase)
                fix_phonemes(phonlist, duration, freq)
                for l in phonlist[1]:
                    s += l + '\n'
                #phons = 'UW'
                #s += '%s {D %d; P %f:0 %f:100}\n' % (phons, duration, freq, freq)
                phrase = ''
                note_t0 = tms
                #say(msg.text, note)
    print s
    say(s)

###

for fn in sys.argv[1:]:
    print "======================================================"
    print fn
    try:
        mid = mido.MidiFile(fn)
        print mid
        for i, track in enumerate(mid.tracks):
            sing_track_idx = -1
            sing_channel = -1
            print('Track {}: {}'.format(i, track.name))
            for msg in track:
                if msg.is_meta and msg.type in ['text', 'lyrics']:
                    sing_track_idx = i
                if i == sing_track_idx and msg.type == 'note_on':
                    sing_channel = msg.channel
            if sing_channel >= 0:
                print "Singing track %d channel %d" % (sing_track_idx, sing_channel)
                sing_track(mid, channels=[sing_channel])
    except:
        print sys.exc_info()
        

#print "*** Sing track", sing_track, "channel", sing_channel

