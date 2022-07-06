import random
import os
import abjad
import sounddevice as sd
from midi2audio import FluidSynth


scale_degrees = {'Do' : 0, 'Re' : 1, 'Mi' : 2, 'Fa' : 3, 'Sol' : 4, 'La' : 5, 'Ti' : 6,} 
diatonic_chords = {'I' : ['Do', 'Mi', 'Sol'], 'ii' : ['Re', 'Fa', 'La'], 'IV' : ['Fa', 'La', 'Do'] , 'V' : ['Sol', 'Ti', 'Re'], 'vii' : ['Ti', 'Re', 'Fa']}
to_F = {'Do' : 'f', 'Re' : 'g', 'Mi' : 'a', 'Fa' : 'bf', 'Sol' : 'c', 'La' : 'd', 'Ti' : 'e',}
to_solfedge = {value : key for key, value in to_F.items()} 

# Support that are used to generate music
def generate_keyboard_and_hs_map():
	"""Function takes no arguments. 
	Generates a keyboard which can translate solfege to specific notes
	Keyboard in the format: 'La': {'d3': 9, 'd4': 21, 'd5': 33}
	Generates a hs_map which can translate to notes to half steps above f2
	HS map is in the format: 'bf2': 5
	Run as : generate_keyboard_and_hs_map()
	"""
	# Variables used to print notes and half steps 
	half_step = 0
	octave = 2
	notes = ['f', 'g', 'a', 'bf', 'c', 'd', 'e']
	current_note = ""
	
	# Generic iterator
	i = 0

	keyboard = {}
	hs_map = {}

	while (current_note + str(octave)) != 'f5':
		current_note = notes[i % 7]

		# Update octave at every C note
		if current_note == 'c':
			octave += 1
		
		# Add note to keybaord
		keyboard.setdefault(to_solfedge[current_note], {})
		keyboard[to_solfedge[current_note]][current_note + str(octave)] = half_step

		# Add note to hs_map
		hs_map[current_note + str(octave)] = half_step

		# Update the number of half steps 
		if current_note in ['a', 'e']:
			half_step += 1
		else:
			half_step += 2

		# Advance to the next note
		i += 1
	return keyboard, hs_map

def find_nearest_note(current_note, pitch_class):
	"""Function takes: 
	* a current note, represented in the form 'g3'. Must be a valid key in hs_map
	* a pitch class, represented by solfege in the form 'Sol'. Must be a valid key in keyboard
	Function returns the note with correct solfege that is closest to the current note.
	Run as: find_nearest_note('g3', 'Do')
	"""
	# Convert the current pitch to a distance above f2 in half steps
	current_pitch = hs_map[current_note]

	# Of all notes with the currect solfege, find the shortest distance to the current pitch
	minval = min([abs(current_pitch - v) for k, v in keyboard[pitch_class].items()])

	# Find all notes that are a minval distance away from the current pitch and have correct solfege (at most, two)
	# Randomly select on of these notes to return
	return random.choice([k for k, v in keyboard[pitch_class].items() if abs(current_pitch - v) == minval])

def transpose_F_major(soprano, bass, prev_soprano, prev_bass):
	"""Function takes:
	* Solfege for the soprano voice at the current beat, in the form 'Do'
	* Solfege for the bass voice at the current beat, in the form 'Ti'
	* The exact pitch of the previous soprano note, in the form 'g3'
	* The exact pitch of the previous bass note, in the form 'g2'
	Function returns the soprano note with correct solfege that is nearest to the previous soprano note
	and the bass note with correct solfege that is nearest to the previous bass note
	This function is identical to transpose_measure_F_major, except that it operates on a beat rather than a full measure 
	Run as: transpose_F_major('Do', 'Ti', 'g3', 'g2')
	"""
	return [find_nearest_note(prev_soprano, soprano), find_nearest_note(prev_bass, bass)]

def transpose_measure_F_major(soprano, bass):
	"""Function takes: 
	* Soprano - a list of solfege in the form ['Do', 'Re']
	* Bass - a list of solfege in the form ['Do', 'Ti']
	Function returns the pitch names for this measure in the form: [['f4', 'g4'], ['f3', 'e3']]
	This function is identical to transpose_F_major, except that it operates on a full measrue rather than a single beat
	Function is run as: transpose_measure_F_major(['Do', 'Re'], ['Do', 'Ti'])
	"""
	s_trans = []
	b_trans = []
	for i in range(len(soprano)):
		if i == 0:
			s_trans.append(find_nearest_note('f4', soprano[i]))
			b_trans.append(find_nearest_note('f3', bass[i]))
		else:
			s_trans.append(find_nearest_note(s_trans[-1], soprano[i]))
			b_trans.append(find_nearest_note(b_trans[-1], bass[i]))
	return [s_trans, b_trans]

# Functions that check voice leading, doublings, etc.
def check_parallel_8(soprano, bass):
	"""Function takes:
	* soprano - a list of two absolute pitches in the form ['g4', 'a4'] 
	* bass - a list of two absolute pitches in the form ['g3', 'a3'] 
	Function returns True if the soprano and bass move in parallel octaves 
	Run as: check_parallel_8(['g4', 'a4'], ['g3', 'a3'])
	"""
	# Find the intervals between the first and second beat soprano and bass
	beat_0_int = (hs_map[soprano[0]] - hs_map[bass[0]])
	beat_1_int = (hs_map[soprano[1]] - hs_map[bass[1]])

	# Check that: the intervals are octaves, and that the pitch classes change (notes are allowed to stay the same)
	if (beat_0_int % 12 == 0) and (beat_1_int % 12 == 0) and (bass[0] != bass[1]):
		return True
	else: 
		return False

def check_parallel_5(soprano, bass):
	"""Function takes:
	* soprano - a list of two absolute pitches in the form ['g4', 'a4'] 
	* bass - a list of two absolute pitches in the form ['c3', 'd3'] 
	Function returns True if the soprano and bass move in parallel fifths 
	Run as: check_parallel_5(['g4', 'a4'], ['c3', 'd3'])
	"""
	# Find the intervals between the first and second beat soprano and bass
	beat_0_int = (hs_map[soprano[0]] - hs_map[bass[0]])
	beat_1_int = (hs_map[soprano[1]] - hs_map[bass[1]])

	# Check that: the intervals are not unisons, the intervals are octaves, and that the pitch classes change (notes are allowed to stay the same)
	if (beat_0_int > 0) and (beat_1_int > 0) and (beat_0_int % 12 == 7) and (beat_1_int % 12 == 7) and (bass[0] != bass[1]):
		return True
	else: 
		return False

def check_tendency_tones(soprano, bass):
	"""Function takes:
	* soprano - a list of two notes reprsented by solfege, eg. ['Ti', 'Do']
	* bass - a list of two notes reprsented by solfege, eg. ['Sol', 'La']
	Returns True if illegal resolution of tendency tones is observed 
	Run as: check_tendency_tones(['Ti', 'Do'], ['Sol', 'La'])
	"""
	if soprano[0] == 'Ti':
		if soprano[1] != 'Do':
			return True
	elif bass[0] == 'Ti':
		if bass[1] != 'Do':
			return True
	return False

# Check six four

# Check melodic leap

#def check_doubling(soprano, bass):
	# WRITE ME 

#def check_range(soprano, bass):
	#### WRITE ME
	### Possibly implement as part of find_nearest_note 

def check_voice_crossing(soprano, bass): 
	"""Function takes:
	* soprano - a list of two absolute pitches in the form ['g3', 'e3'] 
	* bass - a list of two absolute pitches in the form ['e3', 'g3'] 
	Function returns True if the soprano cross at either beat
	Run as: check_voice_crossing(['g3', 'e3'] , ['e3', 'g3'] )
	"""
	for beat in [0,1]:
		s_hs = hs_map[soprano[beat]]
		b_hs = hs_map[bass[beat]]
		if s_hs < b_hs:
			return True
	return False

# # Functions that generate the score
# def realize_combinations(start_chord, end_chord):
# 	"""Function takes:
# 	* start_chord: a string representing a chord, eg. 'I'
# 	* end_chord: a string representing a chord, eg. 'ii'
# 	Both star_chord and end_chord must be valid keys in the diatonic_chords dictionary
# 	Returns the full set of voice leading combinations between start and end chords that do not violate voice leading principles 
# 	Run as: realize combinations('I', 'ii')
# 	"""
# 	combinations = []
# 	for b1 in diatonic_chords[start_chord][0:2]:
# 		for b2 in diatonic_chords[end_chord][0:2]:
# 			for s1 in diatonic_chords[start_chord]:
# 				for s2 in diatonic_chords[end_chord]:
# 					s = [s1, s2]
# 					b = [b1, b2]

possible_extensions = {'I' : ['I','ii','IV','V','vii'], 'ii' : ['ii','V','vii'], 'IV' : ['IV','ii','V'] , 'V' : ['V', 'I'], 'vii' : ['vii','V', 'I']}

def extend(start_chord, soprano, bass):
	"""Function takes:
	* start_chord: a string representing a chord, eg. 'I'
	* bass: a list of absolute pitches, e.g. ['f3']
	* soprano: a list of absolute pitches, e.g. ['a4']
	Returns: 
	* bass: a list of absolute pitches, extended by one note e.g. ['f3', 'g3']
	* soprano: a list of absolute pitches, extended by one note e.g. ['a4', 'bf4']
	* next_chord: a string representing a chord, eg. 'I'
	Function takes the current soprano and bass, finds a legal continuing chord using the possible_extensions dictionary 
	Function selects a permuation of notes that do not violate voice leading principles
	"""
	c = 0
	next_chord = random.choice(possible_extensions[start_chord])
	combinations = []
	for b2 in diatonic_chords[next_chord]:
			for s2 in diatonic_chords[next_chord]:
				s = [soprano[-1], find_nearest_note(soprano[-1], s2)]
				b = [bass[-1], find_nearest_note(bass[-1], b2)]
				c += 1
				if not (check_parallel_8(s, b) or check_parallel_5(s, b) or check_tendency_tones(s, b) or check_voice_crossing(s, b)):
					combinations.append([s, b])
	chosen_extension = random.choice(combinations)
	bass.append(chosen_extension[1][-1])
	soprano.append(chosen_extension[0][-1])
	return([next_chord, soprano, bass])


def make_first_measure():
	"""Function takes no arguments
	Returns two lists of absolute pitches representing soprano and bass in the form: ['f3', 'e3']
	Run as: make_first_measure()
	"""
	bass = ['f3']
	soprano_solfege = random.choice(['Do', 'Mi', 'Sol'])
	soprano = [find_nearest_note('f4', soprano_solfege)]

	measure = extend('I', soprano, bass)

	return(measure)

# Functions that are used for engraving 
def translate_octave(note):
	"""Function takes a note in the format 'f2' 
	Returns the note in engravable notation, eg: 'f,' 
	Run as: translate_octave('f2')
	"""
	pitch = note[:-1]
	octave = int(note[-1])

	if octave == 4:
		pitch += '\''
	elif octave == 5:
		pitch += '\'\''
	elif octave == 2:
		pitch += ','

	return pitch

def make_engravable(soprano, bass):
	"""Function takes: 
	* A list of soprano notes at absolute pitches in the form ['f4', 'g4', 'a4']
	* A list of bass notes at absolute pithces in the form ['f3', 'e3', 'f3']
	Returns the soprano and bass as strings ready to engraved by abjad, in the form: ["f'2 g'4 a'2", 'f2 e4 f2']
	Run as: make_engravable(['f4', 'g4', 'a4'], ['f3', 'e3', 'f3'])
	"""
	s_engrav = []
	b_engrav = []
	for i in range(len(soprano)):
		s_pitch = translate_octave(soprano[i])
		b_pitch = translate_octave(bass[i])

		if i % 2 == 0:
			s_pitch += "2" 
			b_pitch += "2"
		else:
			s_pitch += "4"
			b_pitch += "4"

		s_engrav.append(s_pitch)
		b_engrav.append(b_pitch)

	return [" ".join(s_engrav), " ".join(b_engrav)]

def engrave(soprano, bass):
	"""Function takes: 
	* soprano - a character string denoting absolute pitches and durations, eg. "f'2 g'4 a'2"
	* bass –  a character string denoting absolute pitches and durations, eg. 'f2 e4 f2'
	Function works with abjad to engrave the soprano and bass melodies
	Funtion does not return anything. 
	Run as: engrave("f'2 g'4 a'2", 'f2 e4 f2')
	"""
	time_signature = abjad.TimeSignature((3, 4))
	voice_1 = abjad.Voice(soprano, name="Voice_1")
	voice_2 = abjad.Voice(bass, name="Voice_2")	
	staff_1 = abjad.Staff([voice_1], name="Staff_1")
	staff_2 = abjad.Staff([voice_2], name="Staff_2")

	piano_staff = abjad.StaffGroup(
	    [staff_1, staff_2],
	    lilypond_type="PianoStaff",
	    name="PianoStaff",
	)

	key_signature = abjad.KeySignature("f", "major")
	clef = abjad.Clef("bass")
	abjad.attach(key_signature, voice_1[0])
	abjad.attach(key_signature, voice_2[0])
	abjad.attach(time_signature, voice_1[0])
	abjad.attach(time_signature, voice_2[0])
	abjad.attach(clef, voice_2[0])
	# # attach BPM to notes file
	metronome_mark = abjad.MetronomeMark((1, 4), 120)
	abjad.attach(metronome_mark, voice_1[0])

	score = abjad.Score([piano_staff], name="Score")
	abjad.show(score)

	score_block = abjad.Block(name="score")
	score_block.items.append(score)

	midi_block = abjad.Block(name="midi")
	score_block.items.append(midi_block)

	# # creates lilypond file object
	lilypond_file = abjad.LilyPondFile(items = [score_block])
	return lilypond_file

	

keyboard, hs_map = generate_keyboard_and_hs_map()

# print(keyboard)
# print(hs_map)
# print(find_nearest_note('e4', 'Do'))
# print(hs_map['f3'])
# print(transpose_F_major('Do', 'Ti', 'g3', 'g2'))
# print(transpose_measure_F_major(['Do', 'Re'], ['Do', 'Ti']))
# print(translate_octave('f3'))
# print(make_engravable(['f4', 'g4', 'a4'], ['f3', 'e3', 'f3']))
# #engrave("f'2 g'4 a'2", 'f2 e4 f2')
# print(check_parallel_8(['g4', 'g4'], ['g4', 'g4']))
# print(check_parallel_5(['g4', 'g4'], ['c3', 'c3']))
# print(check_tendency_tones(['Ti', 'Mi'], ['Sol', 'La']))




keyboard, hs_map = generate_keyboard_and_hs_map()
current_chord, soprano, bass = make_first_measure()

for i in range(10):
	current_chord, soprano, bass = extend(current_chord, soprano, bass)
me = make_engravable(soprano, bass)
lp = engrave(me[0], me[1])

print(abjad.persist.as_midi(lp, '~/kirnberger/test'))

sf2_path = '/Users/andrew/Documents/MuseScore3/SoundFonts/MasonHamlin-A-CloseMic-v5.2.sf2'
midi_file = '/Users/andrew//kirnberger/test.midi'

FluidSynth(sf2_path)
FluidSynth(sf2_path).play_midi(midi_file)






























































































