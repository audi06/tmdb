#!/usr/bin/python
# coding=utf-8
#
# Copyright (C) 2018-2023 by dream-alpha
#
# In case of reuse of this source code please do not remove this copyright.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# For more information on the GNU General Public License see:
# <http://www.gnu.org/licenses/>.

from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.config import config
from Components.ScrollLabel import ScrollLabel
from Screens.HelpMenu import HelpableScreen
from Screens.Screen import Screen
from . import tmdbsimple as tmdb
from .__init__ import _
from .Picture import Picture
from .Debug import logger
from .FileUtils import readFile
from .SkinUtils import getSkinPath
from .ConfigScreen import ConfigScreen
from .Json import Json


class ScreenPerson(Picture, Json, Screen, HelpableScreen):
	skin = readFile(getSkinPath("ScreenPerson.xml"))

	def __init__(self, session, cover_ident, backdrop_ident):
		logger.info("cover_ident: %s, backdrop_ident: %s", cover_ident, backdrop_ident)
		Screen.__init__(self, session)
		Picture.__init__(self)
		Json.__init__(self)
		self.session = session
		self.cover_ident = cover_ident
		self.backdrop_ident = backdrop_ident

		self['searchinfo'] = Label(_("Loading..."))
		self['fulldescription'] = self.fulldescription = ScrollLabel("")
		self['cover'] = Pixmap()
		self['backdrop'] = Pixmap()

		self['key_red'] = Label(_("Exit"))
		self['key_green'] = Label()
		self['key_yellow'] = Label()
		self['key_blue'] = Label()

		HelpableScreen.__init__(self)
		self["actions"] = HelpableActionMap(
			self,
			"TMDBActions",
			{
				"cancel": (self.exit, _("Exit")),
				"up": (self.fulldescription.pageUp, _("Selection up")),
				"down": (self.fulldescription.pageDown, _("Selection down")),
				"left": (self.fulldescription.pageUp, _("Page up")),
				"right": (self.fulldescription.pageDown, _("Page down")),
				"red": (self.exit, _("Exit")),
				"menu": (self.setup, _("Setup")),
			},
			-1,
		)

		self.onLayoutFinish.append(self.onFinish)

	def onFinish(self):
		self.showPicture(self["backdrop"], "backdrop", self.backdrop_ident, None)
		self.showPicture(self["cover"], "cover", self.cover_ident, None)
		self.getData()

	def getData(self):
		lang = config.plugins.tmdb.lang.value
		logger.debug("cover_ident: %s", self.cover_ident)
		result = {}
		try:
			json_person = tmdb.People(self.cover_ident).info(language=lang)
			self.parseJsonSingle(result, json_person, "biography")
			if not result["biography"]:
				json_person = tmdb.People(self.cover_ident).info(language="en")
				self.parseJsonSingle(result, json_person, "biography")
			logger.debug("json_person: %s", json_person)
			json_person_movie = tmdb.People(self.cover_ident).movie_credits(language=lang)
			logger.debug("json_person_movie: %s", json_person_movie)
			json_person_tv = tmdb.People(self.cover_ident).tv_credits(language=lang)
			# logger.debug("json_person_tv: %s", json_person_tv)
		except Exception as e:
			logger.error("exception: %s", e)
			self["searchinfo"].setText(_("Data lookup failed."))
			return

		keys = ["name", "birthday", "place_of_birth", "gender", "also_known_as", "popularity"]
		self.parseJsonMultiple(result, json_person, keys)
		logger.debug("result: %s", result)

		self['searchinfo'].setText(result['name'])

		gender = str(result["gender"])
		if gender == "1":
			gender = _("female")
		elif gender == "2":
			gender = _("male")
		elif gender == "divers":
			gender = _("divers")
		else:
			gender = _("None")
		result["gender"] = gender

		self.parseJsonList(result, "also_known_as", ",")
		result["popularity"] = "%.1f" % float(result["popularity"])

		fulldescription = result["birthday"] + ", " \
			+ result["place_of_birth"] + ", " \
			+ result["gender"] + "\n" \
			+ result["also_known_as"] + "\n" \
			+ _("Popularity") + ": " + result["popularity"] + "\n\n" \
			+ result["biography"] + "\n\n"

		logger.debug("fulldescription: %s", fulldescription)

		data_movies = []
		result = {}
		for source in [
			(json_person_movie, ["release_date", "title", "character"], "movie"),
			(json_person_tv, ["first_air_date", "name", "character"], "tv")]:
			self.parseJsonSingle(result, source[0], "cast")
			logger.debug("result: %s", result)
			for cast in result["cast"]:
				logger.debug("cast: %s", cast)
				movie = {}
				self.parseJsonMultiple(movie, cast, source[1])
				logger.debug("movie: %s", movie)
				if source[2] == "movie":
					data_movies.append(("%s %s (%s)" % (movie["release_date"], movie["title"], movie["character"])))
				else:
					data_movies.append(("%s %s (%s)" % (movie["first_air_date"], movie["name"], movie["character"])))
		data_movies.sort(reverse=True)
		movies = "\n".join(data_movies)

		fulldescription += "\n" + _("Known for:") + "\n" + movies
		self["fulldescription"].setText(fulldescription)

	def setup(self):
		self.session.open(ConfigScreen)

	def exit(self):
		self.close(True)
