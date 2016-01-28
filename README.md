Cinelinker
==========

Information courtesy of
IMDb
(http://www.imdb.com).
Used with permission.


Find links between movies actors and directors.

	./linker.py "Bruce Willis" "Emma Stone"

	             Bruce Willis
	 [played in] Moonrise Kingdom [with]
	             Edward Norton
	 [played in] Birdman: Or (The Unexpected Virtue of Ignorance) [with]
	             Emma Stone

The linker will always find one of the shortest path linking the two persons. To remove any ambiguity of the natural language, "one of the shortest path" means that there isn't any shorter path. At least among the paths that are permitted by the data.

If you manage lists of movies on the IMDb web interface, you can export them in CSV and force the linker to use these movies only. For example, `ratings.csv` is the list of my ratings on IMDb. I don't know *Moonrise Kingdom*.

	./linker.py "Bruce Willis" "Emma Stone" --msubset ratings.csv 

	             Bruce Willis
	 [played in] Lucky Number Slevin [with]
	             Stanley Tucci
	 [played in] Easy A [with]
	             Emma Stone

## Installation

This is still a work in progress so the installation process isn't fancy. Furthermore, the data used comes from IMDb, whose [data license](http://www.imdb.com/help/show_leaf?usedatasoftware) seems to indicate that their data can't be republished / altered in any way. For this reason I prefer not to bundle the program with some kind of default data but instead instruct you on how to download it and launch the scripts to manage it.

### 1. Downloading the data

You need to download the IMDb text files [from here](http://www.imdb.com/interfaces). The program requires `actors.list`, `actresses.list` and `directors.list`. Download the corresponding `.gz` compressed archives and place them in the directory of your choice, for example `~/.imdb_data`.

### 2. Indexing the text files

In the cinelinker folder, open the `data.json` configuration file and set the field `extracting` to the directory you've downloaded the IMDb files into. Then enter the following in the command line:

	./extractor.py index

This creates index files in the data files directory, along with the text files themselves.

### 3. Creating the database

Create a new cinelinker database in a directory of your choice, for example `~/.cinelinker`:

	mkdir ~/.cinelinker
	./extractor.py new ~/.cinelinker/my_data

In the cinelinker folder, the directory `lists` contains three CSV files which are lists of most famous actors, actresses and directors. Add them to the database:

	./extractor.py add actors lists/actors.csv ~/.cinelinker/my_data
	./extractor.py add actresses lists/actresses.csv ~/.cinelinker/my_data
	./extractor.py add directors lists/directors.csv ~/.cinelinker/my_data

These commands use the IMDb text files to gather the filmography of the people listed in the CSV files.

### 4. Configuring the linker to use the database

Open `data.json` and set the field `linking` to the path to the database, `home/foobuzz/.cinelinker/my_data` in our case.

### 5. Profit

The linker should now work as explained in the begining of this README.

The linker will now automatically add the filmography of new people your query it with, even those not present in the original CSV files, and try to honor your query.

In a future version, you'll be able to extract *all* of the IMDb data into a true database ready for usage with the linker.
