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
from twisted.internet import reactor, threads
from enigma import eServiceReference
from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.config import config
from Components.ScrollLabel import ScrollLabel
from Screens.MoviePlayer import MoviePlayer
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

	def __init__(self, session, movie, media, cover_url, ident, service_path, backdrop_url):
		logger.debug(
			"movie: %s, media: %s, cover_url: %s, ident: %s, service_path: %s, backdrop_url: %s",
			movie, media, cover_url, ident, service_path, backdrop_url
		)
		Screen.__init__(self, session)
		Picture.__init__(self)
		Json.__init__(self)
		self.title = "TMDB - The Movie Database - " + _("Movie Details")
		self.session = session
		self.movie = movie
		self.media = media
		self.cover_url = cover_url
		self.backdrop_url = backdrop_url
		self.ident = ident
		self.service_path = service_path
		self.files_saved = False
		self.overview = ""

		self["genre"] = Label()
		self["genre_txt"] = Label()
		self["fulldescription"] = self.fulldescription = ScrollLabel("")
		self["rating"] = Label()
		self["votes"] = Label()
		self["votes_brackets"] = Label()
		self["votes_txt"] = Label()
		self["runtime"] = Label()
		self["runtime_txt"] = Label()
		self["year"] = Label()
		self["year_txt"] = Label()
		self["country"] = Label()
		self["country_txt"] = Label()
		self["director"] = Label()
		self["director_txt"] = Label()
		self["author"] = Label()
		self["author_txt"] = Label()
		self["studio"] = Label()
		self["studio_txt"] = Label()

		self.fields = {
			"genre": (_("Genre:"), "-"),
			"fulldescription": (None, ""),
			"rating": (None, "0.0"),
			"votes": (_("Votes:"), "-"),
			"votes_brackets": (None, ""),
			"runtime": (_("Runtime:"), "-"),
			"year": (_("Year:"), "-"),
			"country": (_("Countries:"), "-"),
			"director": (_("Director:"), "-"),
			"author": (_("Author:"), "-"),
			"studio": (_("Studio:"), "-"),
		}

		self["key_red"] = Label(_("Exit"))
		self["key_green"] = Label(_("Crew"))
		self["key_yellow"] = Label(_("Seasons")) if self.media == "tv" else Label("")
		self["key_blue"] = Label(_("more ...")) if self.service_path else Label("")

		self["searchinfo"] = Label()
		self["cover"] = Pixmap()
		self["backdrop"] = Pixmap()
		self["fsklogo"] = Pixmap()
		self["star"] = Pixmap()

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
		logger.debug("movie: %s", self.movie)
		self.showPicture(self["cover"], "cover", self.ident, self.cover_url)
		self.showPicture(self["backdrop"], "backdrop", self.ident, self.backdrop_url)
		DelayTimer(10, self.getData)

	def getData(self):
		self["searchinfo"].setText(_("Looking up: %s ...") % self.movie)
		threads.deferToThread(self.getResult, self.ident, self.media, self.gotData)

	def gotData(self, result):
		if not result:
			self["searchinfo"].setText(_("No results for: %s") % self.movie)
			self.overview = ""
		else:
			self["searchinfo"].setText(self.movie)
			path = "/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/star.png"
			self["star"].instance.setPixmap(LoadPixmap(path))

			fsk = result["fsk"]
			path = "/usr/lib/enigma2/python/Plugins/Extensions/tmdb/pic/fsk_" + fsk + ".png"
			if fsk != "100":
				self["fsklogo"].instance.setPixmap(LoadPixmap(path))

			for field in self.fields:
				logger.debug("field: %s", field)
				logger.debug("result: %s", result[field])
				if self.fields[field][0]:
					self[field + "_txt"].setText(self.fields[field][0])
				if result[field]:
					self[field].setText(result[field])
				else:
					self[field].setText(self.fields[field][1])

			self.overview = result["overview"]

			if self.media == "movie":
				# read video from result
				self.trailer_service = ""
				all_videos = result["videos"]
				self.videos = []
				for video in all_videos:
					if "site" in video and video["site"] == "YouTube":
						self.videos.append(video)
				self["key_yellow"].setText(_("Videos") + " (%s)" % len(self.videos))

	def getResult(self, ident, media, callback):
		lang = config.plugins.tmdb.lang.value
		logger.debug("ident: %s", ident)
		result = {}
		try:
			keys = ["overview", "year", "vote_average", "vote_count", "runtime", "production_countries", "production_companies", "genres", "tagline", "release_date", "seasons", "videos"]
			if media == "movie":
				json_data = tmdb.Movies(ident).info(language=lang, append_to_response="videos")
				# logger.debug("json_data: %s", json_data)
				result = {}
				self.parseJsonSingle(result, json_data, "overview")
				if result["overview"] == "":
					json_data = tmdb.Movies(ident).info(language="en")
				# logger.debug("json_data: %s", json_data)
				# logger.debug("keys: %s", keys)
				self.parseJsonMultiple(result, json_data, keys)
				json_data = tmdb.Movies(ident).credits(language=lang)
				# logger.debug("json_data_cast: %s", json_data)
				keys = ["cast", "crew"]
				self.parseJsonMultiple(result, json_data, keys)
				json_data = tmdb.Movies(ident).releases(language=lang)
				# logger.debug("json_data_fsk: %s", json_data)
				keys = ["countries"]
				self.parseJsonMultiple(result, json_data, keys)
				del json_data
			elif media == "tv":
				json_data = tmdb.TV(ident).info(language=lang)
				# logger.debug("json_data: %s", json_data)
				result = {}
				self.parseJsonSingle(result, json_data, "overview")
				if result["overview"] == "":
					json_data = tmdb.TV(ident).info(language="en")
				# logger.debug("json_data: %s", json_data)
				keys += ["first_air_date", "origin_country", "created_by", "networks", "number_of_seasons", "number_of_episodes"]
				# logger.debug("keys: %s", keys)
				self.parseJsonMultiple(result, json_data, keys)
				json_data = tmdb.TV(ident).credits(language=lang)
				# logger.debug("json_data_cast: %s", json_data)
				keys = ["cast", "crew"]
				self.parseJsonMultiple(result, json_data, keys)
				json_data = tmdb.TV(ident).content_ratings(language=lang)
				# logger.debug("json_data_fsk: %s", json_data)
				keys = ["results"]
				self.parseJsonMultiple(result, json_data, keys)
				del json_data
			else:
				raise Exception("unsupported media: %s" % media)
		except Exception as e:
			logger.error("exception: %s", e)
			result = {}
		else:
			# base for movie and tv series
			result["year"] = result["release_date"][:4]
			result["rating"] = "%s" % format(float(result["vote_average"]), ".1f")
			result["votes"] = str(result["vote_count"])
			result["votes_brackets"] = "(%s)" % str(result["vote_count"])
			result["runtime"] = "%s" % result["runtime"] + " " + _("min")

			country_string = ""
			for country in result["production_countries"]:
				result1 = {}
				self.parseJsonSingle(result1, country, "iso_3166_1")
				if country_string:
					country_string += "/"
				country_string += result1["iso_3166_1"]
			result["country"] = country_string

			genre_string = ""
			for genre in result["genres"]:
				result1 = {}
				self.parseJsonSingle(result1, genre, "name")
				if genre_string:
					genre_string += ", "
				genre_string += result1["name"]
			result["genre"] = genre_string

			cast_string = ""
			for cast in result["cast"]:
				result2 = {}
				self.parseJsonMultiple(result2, cast, ["name", "character"])
				cast_string += "%s (%s)\n" % (result2["name"], result2["character"])
			result["cast"] = cast_string

			crew_string = ""
			director = ""
			author = ""
			for crew in result["crew"]:
				result2 = {}
				self.parseJsonMultiple(result2, crew, ["name", "job"])
				crew_string += "%s (%s)\n" % (result2["name"], result2["job"])
				if result2["job"] == "Director":
					if director:
						director += "\n"
					director += result2["name"]
				if result2["job"] == "Screenplay" or result2["job"] == "Writer":
					if author:
						author += "\n"
					author += result2["name"]
			result["crew"] = crew_string
			result["director"] = director
			result["author"] = author

			studio_string = ""
			for studio in result["production_companies"]:
				result1 = {}
				self.parseJsonSingle(result1, studio, "name")
				if studio_string:
					studio_string += ", "
				studio_string += result1["name"]
			result["studio"] = studio_string

			if media == "movie":
				result["seasons"] = ""

				result1 = {}
				self.parseJsonSingle(result1, result["videos"], "results")
				result["videos"] = result1["results"]

			elif media == "tv":
				# modify data for TV/Series

				year = result["first_air_date"][:4]
				result["year"] = year

				self.parseJsonList(result, "origin_country", "/")
				result["country"] = result["origin_country"]

				director = ""
				for directors in result["created_by"]:
					result1 = {}
					self.parseJsonSingle(result1, directors, "name")
					if director:
						director += "\n"
					director += result1["name"]
				result["director"] = _("Various")
				result["author"] = director

				studio_string = ""
				for studio in result["networks"]:
					result1 = {}
					self.parseJsonSingle(result1, studio, "name")
					if studio_string:
						studio_string += ", "
					studio_string += result1["name"]
				result["studio"] = studio_string

				seasons = result["number_of_seasons"]
				episodes = result["number_of_episodes"]
				result["runtime"] = "%s %s / %s %s" % (seasons, _("Seasons"), episodes, _("Episodes"))

				seasons_string = ""
				for seasons in result["seasons"]:
					result1 = {}
					self.parseJsonMultiple(result1, seasons, ["season_number", "episode_count", "air_date"])
					# logger.debug("seasons: %s", result1)
					if int(result1["season_number"]) >= 1:
						seasons_string += "%s %s: %s %s (%s)\n" % (_("Season"), result1["season_number"], result1["episode_count"], _("Episodes"), result1["air_date"][:4])
				result["seasons"] = seasons_string

			fulldescription = \
				result["tagline"] + "\n" \
				+ "%s, %s, %s" % (result["genre"], result["country"], result["year"]) + "\n\n" \
				+ result["overview"] + "\n\n" + result["cast"] + "\n" + result["crew"] + "\n"\
				+ result["seasons"]
			result["fulldescription"] = fulldescription

			fsk = "100"
			keys = []
			if media == "movie":
				keys = ["countries", "certification"]
			elif media == "tv":
				keys = ["results", "rating"]
			if keys:
				for country in result[keys[0]]:
					result2 = {}
					self.parseJsonMultiple(result2, country, ["iso_3166_1", keys[1]])
					if result2["iso_3166_1"] == "DE":
						fsk = result2[keys[1]].strip("+")
			result["fsk"] = fsk

		reactor.callFromThread(callback, result)  # pylint: disable=E1101

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
			ident = str(self.ident)
			msg = _("File operation results:")
			service_filename = os.path.splitext(self.service_path)[0]
			logger.debug("service_filename: %s", service_filename)
			if option in [3, 6, 7, 8, 9]:
				cover = temp_dir + "cover" + ident + ".jpg"
				if os.path.isfile(cover):
					copyFile(cover, service_filename + ".jpg")
					msg += "\n" + _("Cover saved.")
					self.files_saved = True
					logger.debug("Cover %s.jpg created", service_filename)
				else:
					msg += "\n" + _("No cover available")

			if option in [4, 8, 9]:
				backdrop = temp_dir + "backdrop" + ident + ".jpg"
				if os.path.isfile(backdrop):
					copyFile(backdrop, service_filename + ".bdp.jpg")
					msg += "\n" + _("Backdrop saved.")
					self.files_saved = True
					logger.debug("Backdrop %s.bdp.jpg created", service_filename)
				else:
					msg += "\n" + _("No backdrop available")

			if option in [1, 5, 6, 7, 8]:
				text_file = service_filename + ".txt"
				if self.overview:
					writeFile(text_file, self.overview)
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

	def setup(self):
		self.session.open(ConfigScreen)

	def yellow(self):
		if self.media == "tv":
			self.session.open(ScreenSeason, self.movie, self.ident, self.media)

		# show videos
		elif self.media == "movie" and self.videos:
			videolist = []
			for video in self.videos:
				vKey = video["key"]
				vName = video["name"]
				# sref ="8193:0:1:0:0:0:0:0:0:0:mp_yt%3a//lkL_84wQ9OY:VideoName"
				vLink = "8193:0:1:0:0:0:0:0:0:0:mp_yt%3a//"
				videolist.append((str(vName), str(vLink + "%s:%s" % (vKey, vName))))

			if len(videolist) > 1:
				videolist = sorted(videolist, key=lambda x: x[0])
				self.session.openWithCallback(
					self.videolistCallback,
					ChoiceBox,
					windowTitle=_("TMDB videos"),
					title=_("Please select a video"),
					list=videolist,
				)
			elif len(videolist) == 1:
				self.videolistCallback(videolist[0])

	def videolistCallback(self, ret):
		ret = ret and ret[1]
		if ret:
			self.session.open(MoviePlayer, eServiceReference(ret), streamMode=True, askBeforeLeaving=False)

	def green(self):
		self.session.open(ScreenPeople, self.movie, self.ident , self.media, self.cover_url, self.backdrop_url)

	def exit(self):
		self.close(self.files_saved)
