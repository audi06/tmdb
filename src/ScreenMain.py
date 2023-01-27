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
import base64
from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.config import config
from enigma import eServiceCenter
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.HelpMenu import HelpableScreen
from Screens.ChoiceBox import ChoiceBox
from Screens.Screen import Screen
from . import tmdbsimple as tmdb
from .__init__ import _
from .List import List
from .ConfigScreen import ConfigScreen
from .ScreenMovie import ScreenMovie
from .ScreenPerson import ScreenPerson
from .Utils import temp_dir, cleanText
from .Picture import Picture
from .FileUtils import createDirectory, deleteDirectory, readFile
from .Debug import logger
from .SkinUtils import getSkinPath
from .WebRequests import WebRequests
from .DelayTimer import DelayTimer
from .Json import Json


class ScreenMain(Picture, WebRequests, Json, Screen, HelpableScreen):
	skin = readFile(getSkinPath("ScreenMain.xml"))

	def __init__(self, session, service, mode):
		Screen.__init__(self, session)
		Picture.__init__(self)
		WebRequests.__init__(self)
		Json.__init__(self)
		self.session = session
		tmdb.API_KEY = base64.b64decode("M2I2NzAzYjg3MzRmZWUxYjU5OGRlOWVkN2JiZDNiNDc=")
		tmdb.REQUESTS_SESSION = self.getSession()
		tmdb.REQUESTS_TIMEOUT = (3, 5)
		if not config.plugins.tmdb.api_key.value == "intern":
			tmdb.API_KEY = config.plugins.tmdb.api_key.value
			# logger.debug(API Key User: %s", tmdb.API_KEY)
		self.mode = mode
		self.menu_selection = 0
		self.search_title = _("TMDB: Results for %s")
		self.service_title = ""
		self.page = 1
		self.ident = 1
		self.count = 0
		self.service_path = ""
		self.files_saved = False

		if self.mode == 1:
			self.service_path = service.getPath()
			if os.path.isdir(self.service_path):
				self.service_path = os.path.normpath(self.service_path)
				self.text = os.path.basename(self.service_path)
			else:
				info = eServiceCenter.getInstance().info(service)
				self.text = cleanText(info.getName(service))
		else:
			self.text = cleanText(os.path.splitext(service)[0])

		logger.debug("text: %s", self.text)

		HelpableScreen.__init__(self)
		self["actions"] = HelpableActionMap(
			self,
			"TMDBActions",
			{
				"ok": (self.ok, _("Show details")),
				"cancel": (self.exit, _("Exit")),
				"nextBouquet": (self.nextBouquet, _("Details down")),
				"prevBouquet": (self.prevBouquet, _("Details up")),
				"red": (self.exit, _("Exit")),
				"green": (self.ok, _("Show details")),
				"yellow": (self.searchString, _("Edit search")),
				"blue": (self.menu, _("more ...")),
				"menu": (self.setup, _("Setup")),
				"eventview": (self.searchString, _("Edit search"))
			},
			-1,
		)

		self['searchinfo'] = Label(_("Loading..."))
		self['key_red'] = Label(_("Exit"))
		self['key_green'] = Label(_("Details"))
		self['key_yellow'] = Label(_("Edit search"))
		self['key_blue'] = Label(_("more ..."))
		self['list'] = List()
		self['cover'] = Pixmap()
		self['backdrop'] = Pixmap()

		createDirectory(temp_dir)
		self.onLayoutFinish.append(self.onDialogShow)
		self["list"].onSelectionChanged.append(self.onSelectionChanged)

	def onSelectionChanged(self):
		DelayTimer.stopAll()
		if self["list"].getCurrent():
			DelayTimer(200, self.getInfo)

	def onDialogShow(self):
		logger.debug("text: %s", self.text)
		if self.text:
			self.search()
		else:
			logger.debug("no movie found")
			self['searchinfo'].setText(_("TMDB: No results for %s") % self.text)

	def search(self):
		self['searchinfo'].setText(_("Try to find %s in tmdb ...") % self.text)
		DelayTimer(50, self.searchTMDB)

	def searchTMDB(self):
		lang = config.plugins.tmdb.lang.value
		res = []
		self.count = 0
		json_data = {}
		try:
			if self.menu_selection == 1:
				json_data = tmdb.Movies().now_playing(page=self.page, language=lang)
			elif self.menu_selection == 2:
				json_data = tmdb.Movies().upcoming(page=self.page, language=lang)
			elif self.menu_selection == 3:
				json_data = tmdb.Movies().popular(page=self.page, language=lang)
			elif self.menu_selection == 4:
				json_data = tmdb.Movies(self.ident).similar_movies(page=self.page, language=lang)
			elif self.menu_selection == 5:
				json_data = tmdb.Movies(self.ident).recommendations(page=self.page, language=lang)
			elif self.menu_selection == 6:
				json_data = tmdb.Movies().top_rated(page=self.page, language=lang)
			else:
				json_data = tmdb.Search().multi(query=self.text, language=lang)
			# {u'total_results': 0, u'total_pages': 0, u'page': 1, u'results': []}
			# logger.debug("json_data: %s", json_data)
		except Exception as e:
			logger.error("exception: %s", e)
			self["searchinfo"].setText(_("Data lookup failed."))
			return

		result = {}
		self.parseJsonMultiple(result, json_data, ["total_pages", "results"])
		self.totalpages = result["total_pages"]
		for entry in result["results"]:
			logger.debug("entry: %s", entry)
			self.count += 1

			keys = ["media_type", "id", "title", "name", "release_date", "first_air_date", "poster_path", "backdrop_path", "profile_path"]
			self.parseJsonMultiple(result, entry, keys)

			media = result["media_type"]
			ident = str(result["id"])
			title_movie = result["title"]
			title_series = result["name"]
			title_person = result["name"]
			date_movie = result["release_date"]
			date_tv = result["first_air_date"]
			cover_path = result["poster_path"]
			profile_path = result["profile_path"]
			backdrop_path = result["backdrop_path"]

			title = ""
			if media == "movie":
				title = "%s (%s, %s)" % (title_movie, _("Movie"), date_movie[:4])
			elif media == "tv":
				title = "%s (%s, %s)" % (title_series, _("Series"), date_tv[:4])
			elif media == "person":
				title = "%s (%s)" % (title_person, _("Person"))
			else:
				media = ""

			if media == "person":
				cover_url = "http://image.tmdb.org/t/p/%s/%s" % (config.plugins.tmdb.cover_size.value, profile_path)
			else:
				cover_url = "http://image.tmdb.org/t/p/%s/%s" % (config.plugins.tmdb.cover_size.value, cover_path)
			backdrop_url = "http://image.tmdb.org/t/p/%s/%s" % (config.plugins.tmdb.backdrop_size.value, backdrop_path)

			if ident and title and media:
				res.append(((title, str(ident), media, cover_url, backdrop_url), ))
		self["list"].setList(res)

		if self.menu_selection >= 1:
			self['searchinfo'].setText(_("TMDB:") + str(self.search_title) + " (" + _("page ") + str(self.page) + "/" + str(self.totalpages) + ") " + str(self.service_title))
		else:
			if res:
				self['searchinfo'].setText(_("TMDB: Results for %s") % self.text)
			else:
				self['searchinfo'].setText(_("TMDB: No results for %s") % self.text)

	def getInfo(self):
		if config.plugins.tmdb.skip_to_movie.value and self.count == 1:
			DelayTimer(10, self.ok)
		else:
			self.showPictures()

	def showPictures(self):
		current = self["list"].getCurrent()
		if current:
			ident = current[1]
			cover_url = current[3]
			backdrop_url = current[4]
			self.showPicture(self["cover"], "cover", ident, cover_url)
			self.showPicture(self["backdrop"], "backdrop", ident, backdrop_url)

	def ok(self):
		current = self['list'].getCurrent()
		logger.info("current: %s", current)
		if current:
			title = current[0]
			ident = current[1]
			media = current[2]
			cover_url = current[3]
			backdrop_url = current[4]
			if media in ["movie", "tv"]:
				self.session.openWithCallback(self.callbackScreenMovie, ScreenMovie, title, media, cover_url, ident, self.service_path, backdrop_url)
			elif media == "person":
				self.session.open(ScreenPerson, ident, "")
			else:
				logger.debug("unsupported media: %s", media)

	def callbackScreenMovie(self, files_saved):
		logger.info("files_saved: %s", files_saved)
		self.files_saved = files_saved
		if self.count == 1:
			self.showPictures()

	def menu(self):
		logger.info("...")
		options = [
			(_("TMDB Infos ..."), 0),
			(_("Current movies in cinemas"), 1),
			(_("Upcoming movies"), 2),
			(_("Popular movies"), 3),
			(_("Similar movies"), 4),
			(_("Recommendations"), 5),
			(_("Best rated movies"), 6)
		]
		self.session.openWithCallback(self.menuCallback, ChoiceBox, list=options)

	def menuCallback(self, ret):
		logger.info("ret: %s", ret)
		self.ident = 1
		self.service_title = " "
		self.page = 1
		self.totalpages = 1
		if ret is not None:
			self.search_title = ret[0]
			self.menu_selection = ret[1]
		if self.menu_selection == 4 or self.menu_selection == 5:
			current = self['list'].getCurrent()
			if current:
				self.service_title = current[0]
				self.ident = current[1]
		self.search()

	def nextBouquet(self):
		if self.menu_selection >= 1:
			self.page += 1
			if self.page > self.totalpages:
				self.page = 1
			self.search()

	def prevBouquet(self):
		if self.menu_selection >= 1:
			self.page -= 1
			if self.page <= 0:
				self.page = 1
			self.search()

	def setup(self):
		self.session.open(ConfigScreen)

	def searchString(self):
		self.menu_selection = 0
		self.session.openWithCallback(self.goSearch, VirtualKeyBoard, title=(_("Search for Movie:")), text=self.text)

	def goSearch(self, text):
		if text is not None:
			self.text = text
		self.search()

	def exit(self):
		logger.info("files_saved: %s", self.files_saved)
		self["list"].onSelectionChanged.remove(self.onSelectionChanged)
		deleteDirectory(temp_dir)
		self.close(self.files_saved)
