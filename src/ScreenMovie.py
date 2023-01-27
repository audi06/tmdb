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

import os
from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.config import config
from Components.ScrollLabel import ScrollLabel
from Screens.HelpMenu import HelpableScreen
from Screens.ChoiceBox import ChoiceBox
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Tools.LoadPixmap import LoadPixmap
from . import tmdbsimple as tmdb
from .__init__ import _
from .ConfigScreen import ConfigScreen
from .ScreenPeople import ScreenPeople
from .ScreenSeason import ScreenSeason
from .FileUtils import copyFile, writeFile, readFile, renameFile
from .Picture import Picture
from .Debug import logger
from .SkinUtils import getSkinPath
from .Utils import temp_dir
from .Json import Json
from .DelayTimer import DelayTimer


class ScreenMovie(Picture, Json, Screen, HelpableScreen):
	skin = readFile(getSkinPath("ScreenMovie.xml"))

	def __init__(self, session, title, media, cover_url, ident, service_path, backdrop_url):
		logger.debug(
			"title: %s, media: %s, cover_url: %s, ident: %s, service_path: %s, backdrop_url: %s",
			title, media, cover_url, ident, service_path, backdrop_url
		)
		Screen.__init__(self, session)
		Picture.__init__(self)
		Json.__init__(self)
		self.session = session
		self.title = title
		self.media = media
		self.cover_url = cover_url
		self.backdrop_url = backdrop_url
		self.ident = ident
		self.service_path = service_path
		self.files_saved = False

		self['searchinfo'] = Label(_("Loading..."))
		self['genre'] = Label("-")
		self['genre_txt'] = Label(_("Genre:"))
		self['fulldescription'] = self.fulldescription = ScrollLabel("")
		self['rating'] = Label("0.0")
		self['votes'] = Label("-")
		self['votes_brackets'] = Label("")
		self['votes_txt'] = Label(_("Votes:"))
		self['runtime'] = Label("-")
		self['runtime_txt'] = Label(_("Runtime:"))
		self['year'] = Label("-")
		self['year_txt'] = Label(_("Year:"))
		self['country'] = Label("-")
		self['country_txt'] = Label(_("Countries:"))
		self['director'] = Label("-")
		self['director_txt'] = Label(_("Director:"))
		self['author'] = Label("-")
		self['author_txt'] = Label(_("Author:"))
		self['studio'] = Label("-")
		self['studio_txt'] = Label(_("Studio:"))
		self['key_red'] = Label(_("Exit"))
		self['key_green'] = Label(_("Crew"))
		self['key_yellow'] = Label(_("Seasons")) if self.media == "tv" else Label("")
		self['key_blue'] = Label(_("more ...")) if self.service_path else Label("")
		self['cover'] = Pixmap()
		self['backdrop'] = Pixmap()
		self['fsklogo'] = Pixmap()

		HelpableScreen.__init__(self)
		self["actions"] = HelpableActionMap(
			self,
			"TMDBActions",
			{
				"ok": (self.green, _("Crew")),
				"cancel": (self.exit, _("Exit")),
				"up": (self.fulldescription.pageUp, _("Selection up")),
				"down": (self.fulldescription.pageDown, _("Selection down")),
				"left": (self.fulldescription.pageUp, _("Page up")),
				"right": (self.fulldescription.pageDown, _("Page down")),
				"red": (self.exit, _("Exit")),
				"green": (self.green, _("Crew")),
				"yellow": (self.yellow, _("Seasons")),
				"blue": (self.menu, _("more ...")),
				"menu": (self.setup, _("Setup")),
				"eventview": (self.menu, _("more ..."))
			},
			-1,
		)

		self.onLayoutFinish.append(self.onDialogShow)

	def onDialogShow(self):
		logger.debug("title: %s", self.title)
		self["searchinfo"].setText("%s" % self.title)
		self.showPicture(self["cover"], "cover", self.ident, self.cover_url)
		self.showPicture(self["backdrop"], "backdrop", self.ident, self.backdrop_url)
		DelayTimer(10, self.getData)

	def menu(self):
		if self.service_path:
			options = [
				(_("Save movie description"), 1),
				(_("Delete movie EIT file"), 2),
				(_("Save movie cover"), 3),
				(_("Save movie backdrop"), 4),
				("1+2", 5),
				("1+3", 6),
				("1+2+3", 7),
				("1+2+3+4", 8),
				("3+4", 9)
			]
			self.session.openWithCallback(self.menuCallback, ChoiceBox, list=options)

	def menuCallback(self, ret):
		if ret is not None:
			option = ret[1]
			msg = _("File operation results:")
			service_filename = os.path.splitext(self.service_path)[0]
			logger.debug("service_filename: %s", service_filename)
			if option in [3, 6, 7, 8, 9]:
				cover = temp_dir + "cover" + self.ident + ".jpg"
				if os.path.isfile(cover):
					copyFile(cover, service_filename + ".jpg")
					msg += "\n" + _("Cover saved.")
					self.files_saved = True
					logger.debug("Cover %s.jpg created", service_filename)
				else:
					msg += "\n" + _("No cover available")

			if option in [4, 8, 9]:
				backdrop = temp_dir + "backdrop" + self.ident + ".jpg"
				if os.path.isfile(backdrop):
					copyFile(backdrop, service_filename + ".bdp.jpg")
					msg += "\n" + _("Backdrop saved.")
					self.files_saved = True
					logger.debug("Backdrop %s.bdp.jpg created", service_filename)
				else:
					msg += "\n" + _("No backdrop available")

			if option in [1, 5, 6, 7, 8]:
				text_file = service_filename + ".txt"
				if self.text:
					writeFile(text_file, self.text)
					logger.debug("%s created", text_file)
					msg += "\n" + _("Movie description saved.")
					self.files_saved = True
				else:
					msg += "\n" + _("No movie description available")

			if option in [2, 5, 7, 8]:
				eitFile = service_filename + ".eit"
				if os.path.isfile(eitFile):
					renameFile(eitFile, eitFile + ".bak")
					logger.debug("%s deleted", eitFile)
					msg += "\n" + _("EIT file deleted.")
				else:
					msg += "\n" + _("No EIT file available")

			self.session.open(MessageBox, msg, type=MessageBox.TYPE_INFO)

	def getData(self):
		lang = config.plugins.tmdb.lang.value
		logger.debug("ident: %s", self.ident)
		result = {}
		try:
			if self.media == "movie":
				json_data = tmdb.Movies(self.ident).info(language=lang)
				# logger.debug("json_data: %s", json_data)
				result = {}
				self.parseJsonSingle(result, json_data, "overview")
				if result["overview"] == "":
					json_data = tmdb.Movies(self.ident).info(language="en")
				json_data_cast = tmdb.Movies(self.ident).credits(language=lang)
				# logger.debug("json_data: %s", json_data_cast)
				json_data_fsk = tmdb.Movies(self.ident).releases(language=lang)
				logger.debug("json_data_fsk: %s", json_data_fsk)
			elif self.media == "tv":
				json_data = tmdb.TV(self.ident).info(language=lang)
				result = {}
				self.parseJsonSingle(result, json_data, "overview")
				if result["overview"] == "":
					json_data = tmdb.TV(self.ident).info(language="en")
				# logger.debug("json_data: %s", json_data)
				json_data_cast = tmdb.TV(self.ident).credits(language=lang)
				# logger.debug("json_data_cast: %s", json_data_cast)
				json_data_fsk = tmdb.TV(self.ident).content_ratings(language=lang)
				logger.debug("json_data_fsk: %s", json_data_fsk)
			else:
				logger.debug("unsupported media: %s", self.media)
				return
		except Exception as e:
			logger.error("exception: %s", e)
			self["searchinfo"].setText(_("Data lookup failed."))
			return

		# base for movie and tv series
		seasons_string = ""
		overview = result["overview"]

		keys = ["year", "vote_average", "vote_count", "runtime", "production_countries", "production_companies", "genres", "tagline", "release_date"]
		self.parseJsonMultiple(result, json_data, keys)

		year = result["release_date"][:4]
		self["year"].setText(year)

		vote_average = result["vote_average"]
		self["rating"].setText("%s" % format(float(vote_average), '.1f'))

		vote_count = result["vote_count"]
		self["votes"].setText(str(vote_count))
		self["votes_brackets"].setText("(%s)" % vote_count)

		runtime = result["runtime"]
		self["runtime"].setText("%s min" % runtime)

		country_string = ""
		for country in result["production_countries"]:
			result1a = {}
			self.parseJsonSingle(result1a, country, "iso_3166_1")
			if country_string:
				country_string += "/"
			country_string += result1a["iso_3166_1"]
		self["country"].setText(country_string)

		genre_string = ""
		for genre in result["genres"]:
			result1a = {}
			self.parseJsonSingle(result1a, genre, "name")
			if genre_string:
				genre_string += ", "
			genre_string += result1a["name"]
		self["genre"].setText(genre_string)

		subtitle = result["tagline"]

		result2 = {}
		self.parseJsonMultiple(result2, json_data_cast, ["cast", "crew"])

		cast_string = ""
		for cast in result2["cast"]:
			result2a = {}
			self.parseJsonMultiple(result2a, cast, ["name", "character"])
			cast_string += "%s (%s)\n" % (result2a["name"], result2a["character"])

		crew_string = ""
		director = ""
		author = ""
		for crew in result2["crew"]:
			result2a = {}
			self.parseJsonMultiple(result2a, crew, ["name", "job"])
			crew_string += "%s (%s)\n" % (result2a["name"], result2a["job"])
			if result2a["job"] == "Director":
				if director:
					director += "\n"
				director += result2a["name"]
			if result2a["job"] == "Screenplay" or result2a["job"] == "Writer":
				if author:
					author += "\n"
				author += result2a["name"]
		self["director"].setText(director)
		self["author"].setText(author)

		studio_string = ""
		for studio in result["production_companies"]:
			result1a = {}
			self.parseJsonSingle(result1a, studio, "name")
			if studio_string:
				studio_string += ", "
			studio_string += result1a["name"]
		self["studio"].setText(studio_string)

		# modify data for TV/Series
		if self.media == "tv":
			keys = ["seasons", "first_air_date", "origin_country", "created_by", "networks", "number_of_seasons", "number_of_episodes", "overview"]
			self.parseJsonMultiple(result, json_data, keys)

			year = result["first_air_date"][:4]
			self["year"].setText(year)

			self.parseJsonList(result, "origin_country", "/")
			self["country"].setText(result["origin_country"])

			director = ""
			for directors in result["created_by"]:
				result1a = {}
				self.parseJsonSingle(result1a, directors, "name")
				if director:
					director += "\n"
				director += result1a["name"]
			self["director"].setText(_("Various"))
			self["author"].setText(director)

			studio_string = ""
			for studio in result["networks"]:
				result1a = {}
				self.parseJsonSingle(result1a, studio, "name")
				if studio_string:
					studio_string += ", "
				studio_string += result1a["name"]
			self['studio'].setText(studio_string)

			seasons = result["number_of_seasons"]
			episodes = result["number_of_episodes"]
			runtime = "%s %s / %s %s" % (seasons, _("Seasons"), episodes, _("Episodes"))
			self["runtime"].setText(runtime)

			seasons_string = ""
			for seasons in result["seasons"]:
				result1a = {}
				self.parseJsonMultiple(result1a, seasons, ["season_number", "episode_count", "air_date"])
				logger.debug("seasons: %s", result1a)
				if int(result1a["season_number"]) >= 1:
					seasons_string += "%s %s: %s %s (%s)\n" % (_("Season"), result1a["season_number"], result1a["episode_count"], _("Episodes"), result1a["air_date"][:4])

		fulldescription = \
			subtitle + "\n" \
			+ "%s, %s, %s" % (genre_string, country_string, year) + "\n\n" \
			+ overview + "\n\n" + cast_string + "\n" + crew_string + "\n"\
			+ seasons_string
		self["fulldescription"].setText(fulldescription)

		fsk = "100"
		keys = []
		if self.media == "movie":
			keys = ["countries", "certification"]
		elif self.media == "tv":
			keys = ["results", "rating"]
		if keys:
			result3 = {}
			self.parseJsonSingle(result3, json_data_fsk, keys[0])
			for country in result3[keys[0]]:
				result3a = {}
				self.parseJsonMultiple(result3a, country, ["iso_3166_1", keys[1]])
				if result3a["iso_3166_1"] == "DE":
					fsk = result3a[keys[1]].strip("+")
		path = "/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/fsk_" + fsk + ".png"
		if fsk != "100":
			self["fsklogo"].instance.setPixmap(LoadPixmap(path))
			self["fsklogo"].show()
		else:
			self["fsklogo"].hide()

	def setup(self):
		self.session.open(ConfigScreen)

	def yellow(self):
		if self.media == "tv":
			self.session.open(ScreenSeason, self.title, self.ident, self.media)

	def green(self):
		self.session.open(ScreenPeople, self.title, self.ident , self.media, self.cover_url, self.backdrop_url)

	def exit(self):
		self.close(self.files_saved)
