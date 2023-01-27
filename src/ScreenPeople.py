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
from Screens.HelpMenu import HelpableScreen
from Screens.Screen import Screen
from . import tmdbsimple as tmdb
from .__init__ import _
from .List import List
from .ConfigScreen import ConfigScreen
from .ScreenPerson import ScreenPerson
from .Picture import Picture
from .Debug import logger
from .SkinUtils import getSkinPath
from .FileUtils import readFile
from .DelayTimer import DelayTimer
from .Json import Json


class ScreenPeople(Picture, Screen, Json, HelpableScreen):
	skin = readFile(getSkinPath("ScreenPeople.xml"))

	def __init__(self, session, movie, ident, media, cover_url, backdrop_url):
		logger.info("movie %s, ident: %s, media: %s, cover_url: %s, backdrop_url: %s", movie, ident, media, cover_url, backdrop_url)
		Screen.__init__(self, session)
		Picture.__init__(self)
		Json.__init__(self)
		self.session = session
		self.movie = movie
		self.ident = ident
		self.media = media
		self.cover_url = cover_url
		self.backdrop_url = backdrop_url

		self['searchinfo'] = Label(_("Loading..."))
		self['key_red'] = Label(_("Exit"))
		self['key_green'] = Label(_("Details"))
		self["key_yellow"] = Label()
		self['key_blue'] = Label()
		self['list'] = self.list = List()
		self['cover'] = Pixmap()
		self['backdrop'] = Pixmap()

		HelpableScreen.__init__(self)
		self["actions"] = HelpableActionMap(
			self,
			"TMDBActions",
			{
				"ok": (self.ok, _("Show details")),
				"cancel": (self.exit, _("Exit")),
				"up": (self.list.moveUp, _("Selection up")),
				"down": (self.list.moveDown, _("Selection down")),
				"right": (self.list.pageDown, _("Page down")),
				"left": (self.list.pageUp, _("Page down")),
				"red": (self.exit, _("Exit")),
				"green": (self.ok, _("Show details")),
				"menu": (self.setup, _("Setup"))
			},
			-1,
		)

		self.onLayoutFinish.append(self.onFinish)
		self["list"].onSelectionChanged.append(self.onSelectionChanged)

	def onSelectionChanged(self):
		DelayTimer.stopAll()
		if self["list"].getCurrent():
			DelayTimer(200, self.getInfo)

	def onFinish(self):
		logger.debug("movie: %s", self.movie)
		self['searchinfo'].setText("%s" % self.movie)
		self.showPicture(self["backdrop"], "backdrop", self.ident, self.backdrop_url)
		self.searchTMDB()

	def searchTMDB(self):
		lang = config.plugins.tmdb.lang.value
		self['searchinfo'].setText("%s" % self.movie)
		res = []
		try:
			if self.media == "movie":
				json_data_cast = tmdb.Movies(self.ident).credits(language=lang)
				# logger.debug("json_data_cast: %s", json_data_cast)
			else:
				json_data_cast = tmdb.TV(self.ident).credits(language=lang)
				# logger.debug("json_data_cast: %", json_data_cast)
				json_data_seasons = tmdb.TV(self.ident).info(language=lang)
				# logger.debug("json_data_seasons: %s", json_data_seasons)
		except Exception as e:
			logger.error("exception: %s", e)
			self["searchinfo"].setText(_("Data lookup failed."))
			return

		result1 = {}
		self.parseJsonSingle(result1, json_data_cast, "cast")
		for casts in result1["cast"]:
			result2 = {}
			keys = ["id", "name", "profile_path", "character"]
			self.parseJsonMultiple(result2, casts, keys)
			cover_ident = str(result2["id"])
			title = "%s (%s)" % (result2["name"], result2["character"])
			cover_path = result2["profile_path"]
			cover_url = "http://image.tmdb.org/t/p/%s/%s" % (config.plugins.tmdb.cover_size.value, cover_path)
			if cover_ident and title:
				res.append(((title, cover_url, cover_ident), ))

		if not self.media == "movie":
			season_number = 1
			result = {}
			self.parseJsonSingle(result, json_data_seasons, "seasons")
			for season in result["seasons"]:
				# logger.debug("######: %s", season)
				result2 = {}
				keys2 = ["season_number", "id", "name", "air_date"]
				self.parseJsonMultiple(result2, season, keys2)
				season_number = result2["season_number"]
				# logger.debug("#########: %s", result2["season_number"])
				cover_ident = str(result2["id"])
				title = result2["name"]
				date = "(%s)" % result2["air_date"][:4]
				res.append(((title + " " + date, None, ""), ))

				json_data_season = tmdb.TV_Seasons(self.ident, season_number).credits(language=lang)
				result3 = {}
				self.parseJsonSingle(result3, json_data_season, "cast")
				for casts in result3["cast"]:
					result4 = {}
					keys4 = ["id", "name", "character", "profile_path"]
					self.parseJsonMultiple(result4, casts, keys4)
					cover_ident = str(result4["id"])
					title = "%s (%s)" % (result4["name"], result4["character"])
					cover_path = result4["profile_path"]
					cover_url = "http://image.tmdb.org/t/p/%s/%s" % (config.plugins.tmdb.cover_size.value, cover_path)

					if cover_ident and title:
						res.append((("    " + title, cover_url, cover_ident), ))
		self['list'].setList(res)
		self.getInfo()

	def getInfo(self):
		cover_url = self['list'].getCurrent()[1]
		cover_ident = self['list'].getCurrent()[2]
		self.showPicture(self["cover"], "cover", cover_ident, cover_url)

	def ok(self):
		current = self['list'].getCurrent()
		if current:
			cover_ident = current[2]
			if cover_ident:
				self.session.open(ScreenPerson, cover_ident, self.ident)

	def setup(self):
		self.session.open(ConfigScreen)

	def exit(self):
		self["list"].onSelectionChanged.remove(self.onSelectionChanged)
		self.close()
