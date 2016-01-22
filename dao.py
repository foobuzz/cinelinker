import json
from constants import FANCY_JOBNAMES


class Database:

	def __init__(self, path):
		self.path = path
		self.p_path, self.m_path = get_db_paths(path)
		with open(self.p_path) as people_f, \
			 open(self.m_path) as movies_f:
			self.people = json.load(people_f)
			self.movies = json.load(movies_f)

	def save(self):
		with open(self.p_path, 'w', encoding='utf8') as people_f, \
			 open(self.m_path, 'w', encoding='utf8') as movies_f:
			json.dump(self.people, people_f, ensure_ascii=False)
			json.dump(self.movies, movies_f, ensure_ascii=False)

	def add_person(self, person, profile, filename, set_birth=False):
		serial, movies = person
		self.add2people(person, profile, filename, set_birth)
		for title, year, *rest in movies:
			self.add2movies(title, year, profile.name, serial, filename)

	def add2people(self, person, profile, filename, set_birth):
		serial, movies = person
		known = self.people.get(profile.name)
		filmo = []
		for title, year, *_ in movies:
			filmo.append((title, year, FANCY_JOBNAMES[filename]))
		filmoset = set(filmo)
		entry = [
			serial,
			[filename],
			profile.birthdate if set_birth else None,
			filmo
		]
		if known is None:
			self.people[profile.name] = [entry]
		else:
			the_one = None
			for ent in known:
				ser, *_ = ent
				if ser == serial:
					the_one = ent
			if the_one is None:
				known.append(entry)
			else:
				if set_birth and the_one[2] is None and \
				profile.birthdate is not None:
					the_one[2] = profile.birthdate
				origin_filmoset = set(tuple(m) for m in the_one[3])
				new_filmo = filmoset | origin_filmoset
				the_one[3] = list(new_filmo)
				if filename not in the_one[1]:
					the_one[1].append(filename)

	def add2movies(self, title, year, name, serial, filename):
		key = ';'.join([title, year])
		known_crew = self.movies.get(key)
		entry = [name, serial, FANCY_JOBNAMES[filename]]
		if known_crew is None:
			self.movies[key] = [entry]
		else:
			if entry not in known_crew:
				known_crew.append(entry)

	def get_filmo(self, name, serial):
		candidates = self.people.get(name)
		if candidates is None:
			return None
		else:
			for serial, *_, filmo in candidates:
				if serial == serial:
					return filmo


def get_db_paths(path):
	return path+'_people.json', path+'_movies.json'


def create_new_db(path):
	p_path, m_path = get_db_paths(path)
	with open(p_path, 'w') as people_f, \
		 open(m_path, 'w') as movies_f:
		json.dump({}, people_f)
		json.dump({}, movies_f)
