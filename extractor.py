#!/usr/bin/env python3

import sys, csv, re, json
import os.path as op
from collections import namedtuple, OrderedDict
import dao
from constants import FANCY_JOBNAMES


KNOWNFOR = re.compile('^(.+), <a href=".*">(.+)</a>$') # I like to live dangerously

NEW = re.compile('^([^,]+), ([^(	]+)( \((.+)\))?	+(.+)$')
PARSING = re.compile('^	+(.+)$')

MOVIE_DIR = re.compile('^([^"].+[^"]) \((.{4})\)$')
MOVIE_ACT = re.compile('^([^"].+[^"]) \((.{4})\)(  \(voice\))?  \[(.*)\](  <([0-9]+)>)?$')
MOVIE_PHO = re.compile('^([^"].+[^"]) \((.{4})\)(  \(director of photography\))?$')

MOVIE_REGEX = OrderedDict([
	('actors.list', MOVIE_ACT),
	('actresses.list', MOVIE_ACT),
	('directors.list', MOVIE_DIR),
])

FILENAMES = {
	'actors': ['actors.list'],
	'actresses': ['actresses.list'],
	'comedians': ['actors.list', 'actresses.list'],
	'directors': ['directors.list'],
}

PAD = ' '
DEFAULT_INDEX_LEN = 4
DEFAULT_INDEX_SUFFIX = '.index.json'


Profile = namedtuple('Profile', 'name birthdate known_for')


def iter_imdb_csv(filename):
	""" Iterates over the people of a CSV IMDb list. Yields 3-tuples in the
		form:
			(name, known_for, birth)
		where:
			known_for is the title of a movie the person is known for;
			birth is the date of birth of the person in ISO standard
			(YYYY-MM-DD)
	"""
	with open(filename, encoding='utf8', newline='') as csvfile:
		reader = csv.reader(csvfile)
		next(reader) # Skipping the header line
		for row in reader:
			if row == []:
				continue
			name, known_for, birth = row[-3:]
			match = re.match(KNOWNFOR, known_for)
			if match is not None:
				known_for = match.group(2)
			else:
				known_for = None
			yield name, birth, known_for


def add_people(profiles, database, datadir, lists, verbose=True):
	added = set()
	candict = OrderedDict()
	for filename in lists:
		regex = MOVIE_REGEX[filename]
		filepath = op.join(datadir, filename)
		indexpath = op.join(datadir, filename + DEFAULT_INDEX_SUFFIX)
		with open(indexpath) as index_file:
			index = json.load(index_file)
			keylen = len(next(iter(index.keys())))
		with open(filepath, encoding='latin-1') as datafile:
			if verbose:
				print('\n'+filename)
				print('='*len(filename))
			for profile in profiles:
				key = get_key(get_last_name(profile.name), keylen)
				start = index.get(key)
				if start is None:
					continue
				datafile.seek(start)
				seen = False
				candidates = []
				for _, current_pos, lastname, firstname, serial, films in iter_imdb_list(datafile, regex):
					current_key = get_key(lastname, keylen)
					if current_key != key:
						break
					serial = serial if serial is not None else ''
					fullname = ' '.join([firstname, lastname])
					if fullname != profile.name:
						if seen:
							break
						else:
							continue
					else:
						seen = True
						candidates.append((serial, list(films)))
				filtered = filter_candidates(candidates, profile)
				if len(filtered) == 1:
					if verbose: print('*', profile.name)
					added.add(profile)
					database.add_person(filtered[0], profile, filename,
						len(lists) == 1)
					# This len(lists) == 1 will be used to know if we should
					# set the birth of the person in the database.
				elif len(filtered) > 1:
					prof_dict = candict.get(profile)
					if prof_dict is None:
						candict[profile] = {filename: filtered}
					else:
						prof_dict[filename] = filtered
	if len(candict) != 0:
		added |= launch_interactive_find(candict, database)
	return added


def filter_candidates(candidates, profile):
	if len(candidates) <= 1:
		return candidates
	elif len(candidates) > 1:
		refined = []
		for cand in candidates:
			serial, movies = cand
			if len(movies) != 0:
				refined.append(cand)
			for title, year, *rest in movies:
				if title == profile.known_for and profile.known_for is not None:
					return [cand]
		return refined


def launch_interactive_find(candict, database):
	added = set()
	for profile, lists in candict.items():
		been_added = False
		lists_list = list(lists.keys())
		lists_list.sort()
		if len(lists_list) == 1:
			wanted_lists = lists_list
		else:
			wanted_lists = []
			print("I've multiple candidates named {} for the following "
				"profession:".format(profile.name))
			for i, lis in enumerate(lists_list):
				print(" {}. {}".format(i+1, lis))
			ans = input("Enter one or multiple choices separated by "
				"semi-colons. Or just hit enter if none of these "
				"professions interests you > ")
			if ans == '':
				continue
			wanted_indexes = [int(a.strip()) for a in ans.split(';')]
			for i in wanted_indexes:
				wanted_lists.append(lists_list[i-1])

		for filename in wanted_lists:
			print('\n==> I found multiple {} named {}'.format(FANCY_JOBNAMES[filename],
	 			profile.name))
			for i, cand in enumerate(lists[filename]):
				serial, movies = cand
				print(' {}. {} {}, who was involved in {} movies, some of which are:'.format(i+1,
					profile.name, serial, len(movies)))
				for title, year, *rest in movies[:10]:
					print('   {}, {}'.format(title, year))
			ans = input("Enter one or multiple choices separated by semi-colons. "
				"Or just hit enter if none of these persons interests you > ")
			if ans == '':
				continue
			wanted_indexes = [int(a.strip()) for a in ans.split(';')]
			been_added = wanted_indexes != []
			for i in wanted_indexes:
				database.add_person(lists[filename][i-1], profile, filename)

		if been_added:
			added.add(profile)

	print('\nAlright there mate, thanks!')
	return added


def get_last_name(fullname):
	components = fullname.split()
	if len(components) == 1:
		return fullname
	else:
		return ' '.join(components[1:])


def get_key(string, length, pad=None):
	final = string[:length]
	if pad is not None:
		while len(final) < length:
			final += pad
	return final


def index_imdb(datafilepath, length):
	filename = op.basename(datafilepath)
	regex = MOVIE_REGEX[filename]
	print('Indexing {}...'.format(filename))
	previous_key = PAD*4
	index = {previous_key: 0}
	with open(datafilepath, encoding='latin-1') as datafile:
		for stuff in iter_imdb_list(datafile, regex):
			byteno, _, lastname, _, _, _ = stuff
			key = get_key(lastname, length, PAD)
			if key != previous_key:
				index[key] = byteno
				previous_key = key
			print('{}\r'.format(key), end='')
	return index


def iter_imdb_list(list_f, film_re, stop=None):
	""" An iterator on people listed in an IMDb data file. Yields 4-tuples
	    in the form:
	    	(lastname, firstname, serial, movies)
	    where:
	    	serial is a string of a roman numeral or None
	    	movies is an iterator on the person's movies.
	    movies yields 3-tuples in the form:
	    	(title, year, rest)
	    where:
	    	rest is a tuple containing additional info

	    If movies is iterated though, it must be done when the main iterator is
	    stopped at the movies' person. This is because the two iterators share
	    the same file descriptor and only one pass is done on it without any use
	    of sequences.
	"""

	state = 'WAITING NEXT'
	line = list_f.readline()
	while line != '':
		if line == '\n':
			state = 'WAITING NEXT'
		elif state == 'WAITING NEXT':
			match = re.match(NEW, line)
			if match is None:
				state = 'SKIPPING'
			else:
				lastname, firstname, _, serial, movie = match.groups()
				movies = iter_movies(list_f, movie, film_re)
				current_pos = list_f.tell()
				last_line_length = len(line.encode('latin-1'))
				name_pos = current_pos - last_line_length
				yield name_pos, current_pos, lastname, firstname, serial, movies
		# We don't have to worry about whether someone iterated though movies.
		# If the iterator is called and exhausted, then the cursor is at a
		# newline line and a new person will be detected next loop call.
		# Otherwise we're somewhere inside some filmography and at the next
		# loop call the regex identifying a new person will fail, putting the
		# state in SKIPPING.
				if stop is not None and name_pos == stop:
					break
		line = list_f.readline()


def iter_movies(list_f, first, film_re):
	title, year, rest = parse_movie(film_re, first)
	if title is not None:
		yield title, year, rest
	line = None
	while line != '\n' and line != '':
		line = list_f.readline()
		match = re.match(PARSING, line)
		if match is not None:
			movie = match.group(1)
			title, year, rest = parse_movie(film_re, movie)
			if title is not None:
				yield title, year, rest


def parse_movie(film_re, movie):
	moviematch = re.match(film_re, movie)
	if moviematch is not None:
		title, year, *rest = moviematch.groups()
		return title, year, rest
	else:
		return None, None, None


if __name__ == '__main__':	
	with open('data.json', encoding='utf8') as config:
		datadir = json.load(config)['extracting']

	if sys.argv[1] == 'new':
		db_name = sys.argv[2]
		dao.create_new_db(db_name)

	elif sys.argv[1] == 'index':
		if len(sys.argv) == 2:
			to_index = list(iter(MOVIE_REGEX.keys()))
		else:
			to_index = [sys.argv[2]]
		for filename in to_index:
			datafilepath = op.join(datadir, filename)
			indexfname = datafilepath + DEFAULT_INDEX_SUFFIX
			index = index_imdb(datafilepath, DEFAULT_INDEX_LEN)
			with open(indexfname, 'w', encoding='utf8') as index_f:
				json.dump(index, index_f, ensure_ascii=False)

	elif sys.argv[1] == 'add':
		remaining = sys.argv[2:]
		if len(remaining) == 2:
			sourcefile, db_name = remaining
			lists = next(iter(MOVIE_REGEX.keys()))
		elif len(remaining) == 3:
			profession, sourcefile, db_name = remaining
			lists = FILENAMES[profession]
		database = dao.Database(db_name)
		profiles = []
		for item in iter_imdb_csv(sourcefile):
			profiles.append(Profile(*item))
		profiles.sort(key=lambda p: get_last_name(p.name))
		add_people(profiles, database, datadir, lists)
		database.save()
