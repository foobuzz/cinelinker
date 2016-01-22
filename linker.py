#!/usr/bin/env python3

import sys, argparse, csv, json, time
from collections import namedtuple, deque
import dao, extractor
from constants import *


PersonNode = namedtuple('PersonNode', 'person parent part1 movie part2 depth')


LINK_TO = {
	'Actor': 'played in',
	'Actress': 'played in',
	'Director': 'directed'
}

LINK_FROM = {
	'Actor': 'with',
	'Actress': 'with',
	'Director': 'directed by'
}


def link(personA, personB, database, max_depth, allowed_people,
		allowed_movies, verbose=False):
	pA = PersonNode(personA, None, None, None, None, 0)
	queue = deque()
	queue.append(pA)
	people_seen = set()
	people_seen.add(personA)
	movies_seen = set()
	while queue:
		c_node = queue.popleft()
		name, serial = c_node.person
		if verbose: print('# Checking person: {} ({})'.format(name, serial))
		films = database.get_filmo(name, serial)
		for title, year, part1 in films:
			if verbose: print('  * Checking movie: {} ({})'.format(title, year))
			already_seen = (title, year) in movies_seen
			not_allowed = allowed_movies is not None and (title, year) not in allowed_movies
			if already_seen:
				if verbose: print('    This movie has already been examined. Next one...')
				continue
			if not_allowed:
				if verbose: print('    This movie is not allowed. Next one...')
				continue
			movie_id = ';'.join([title, year])
			crew = database.movies[movie_id]
			if verbose: print("    Checking movie crew")
			for buddy, bserial, part2 in crew:
				buddy_id = (buddy, bserial)
				if verbose: print('      > Checking {} ({})'.format(buddy, bserial))
				already_seen = buddy_id in people_seen
				not_allowed = allowed_people is not None and buddy_id not in allowed_people
				if already_seen:
					if verbose: print('      This person has already been screened. Next one...')
					continue
				if not_allowed:
					if verbose: print('      This person is not allowed. Next one...')
					continue					
				if buddy_id == personB:
					if verbose: print("      Target found!!! Over.")
					return PersonNode(buddy_id, c_node, part1, title, part2, 0)
				n_depth = c_node.depth + 1
				if max_depth > 0 and n_depth > max_depth:
					continue
				if verbose: print('      Appending this person to the queue')
				n_node = PersonNode(buddy_id, c_node, part1, title, part2, n_depth)
				queue.append(n_node)
				people_seen.add((buddy, bserial))
			movies_seen.add((title, year))


def show_all(personNode):
	print()
	current = personNode
	while current is not None:
		print(' '*13 + current.person[0])
		part1, part2 = current.part1, current.part2
		if part1 is not None:
			label1 = '[{}]'.format(LINK_TO[part2])
			label2 = '[{}]'.format(LINK_FROM[part1])
			print('{:>12} {} {}'.format(label1, current.movie, label2))
		current = current.parent


def get_person(name, database):
	candidates = database.people.get(name)
	if candidates is None:
		return None
	elif len(candidates) == 1:
		serial = candidates[0][0]
		return (name, serial)
	else:
		return interactive_find(name, candidates)


def interactive_find(name, candidates):
	print(("I know multiple people named {}. ".format(name) +
		"Can you tell me who you're thinking about?"))
	for i, (serial, _, birth, filmo) in enumerate(candidates):
		if birth is None:
			print("{}. {} {}, who was involved in:".format(i+1, name,
				serial))	
		else:
			print("{}. {} {}, born {} who was involved in:".format(i+1, name,
				serial, birth))
		for title, year, job in filmo[:10]:
			print('  * {} ({}) as {}'.format(title, year, job))
	ans = input("You've already made the choice. Now you have to understand it > ")
	serial, *_ = candidates[int(ans.strip())-1]
	return (name, serial)


def populate_set(function):
	def wrapper(filepath):
		allowed = set()
		with open(filepath, encoding='utf8') as csvfile:
			reader = csv.reader(csvfile)
			next(reader)
			for row in reader:
				if row == []:
					continue
				else:
					allowed.add(function(row))
		return allowed
	return wrapper


@populate_set
def get_allowed_movies(row):
	return (row[5], row[11])

@populate_set
def get_allowed_people(row):
	return (row[5], row[8])


if __name__ == '__main__':
	start_opening = time.perf_counter()
	parser = argparse.ArgumentParser(
		description="""Cineliner. Find links between movie personalities.\n
		Information courtesy of
			IMDb
			(http://www.imdb.com).
		Used with permission.\n\n""")
	parser.add_argument('nameA')
	parser.add_argument('nameB')
	parser.add_argument('--limit', type=int, default=-1,
		help="""Limit the number of movies used to link the two personalities.
			Use -1 for no limit, which is the default""")
	parser.add_argument('--msubset',
		help="""The path to an IMDb-exported CSV files which is a list of movies.
			The link between the two personalities will only pass by
			movies in the list""")
	parser.add_argument('--psubset',
		help="""The path to an IMDb-exported CSV file which is a list of people.
			The link between the two personalities will only pass by
			people in the list""")
	parser.add_argument('--perf', action='store_true',
		help="""Show time performance of execution""")
	parser.add_argument('--trace', action='store_true',
		help="""Show the algorithm in action""")

	args = parser.parse_args()

	with open('data.json', encoding='utf8') as config:
		config_dict = json.load(config)
		db_name = config_dict['linking']
		datadir = config_dict['extracting']
	database = dao.Database(db_name)

	opening = time.perf_counter() - start_opening
	start_lookup = time.perf_counter()

	allowed_movies = None
	if args.msubset is not None:
		allowed_movies = get_allowed_movies(args.msubset)
	allowed_people = None
	if args.psubset is not None:
		allowed_people = get_allowed_people(args.psubset)

	altered_database = False
	personA = get_person(args.nameA, database)
	personB = get_person(args.nameB, database)
	to_add = []
	for result, name in zip([personA, personB], [args.nameA, args.nameB]):
		if result is None:
			to_add.append(extractor.Profile(name=name, birthdate=None,
				known_for=None))
	if to_add != []:
		lists = list(FANCY_JOBNAMES.keys())
		added = extractor.add_people(to_add, database, datadir, lists, False)
		altered_database = True
		missing = set(to_add) - added
		if len(missing) != 0:
			for name, *_ in missing:
				print("I don't know {}".format(name))
			sys.exit()
	if personA is None:
		personA = get_person(args.nameA, database)
	if personB is None:
		personB = get_person(args.nameB, database)

	if personA == personB:
		print()
		print(13*' '+args.nameA)
		print()
		sys.exit()

	lookup = time.perf_counter() - start_lookup
	start_linking = time.perf_counter()

	path = link(personB, personA, database,
		args.limit-1, allowed_people, allowed_movies,
		args.trace)
	linking = time.perf_counter() - start_linking

	start_display = time.perf_counter()
	if path is not None:
		show_all(path)
	else:
		print('No link.')
	display = time.perf_counter() - start_display

	if args.perf:
		print()
		print('Opening data:  {:.3f}'.format(opening))
		print('Lookup:  {:.3f}'.format(lookup))
		print('Linking: {:.3f}'.format(linking))
		print('Total:   {:.3f}'.format(opening + lookup + linking + display))

	if altered_database:
		database.save()
