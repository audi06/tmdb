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

from twisted.internet import reactor
from Components.config import config
from . import tmdbsimple as tmdb
from .__init__ import _
from .Debug import logger
from .Json import Json


class SearchMain(Json):

	def __init__(self):
		Json.__init__(self)

	def getResult(self, menu_selection, text, ident, page, callback):
		logger.info("menu_selection: %s, text: %s, ident: %s, page: %s", menu_selection, text, ident, page)
		lang = config.plugins.tmdb.lang.value
		res = []
		totalpages = 0
		json_data = {}
		try:
			if menu_selection == 1:
				json_data = tmdb.Movies().now_playing(page=page, language=lang)
			elif menu_selection == 2:
				json_data = tmdb.Movies().upcoming(page=page, language=lang)
			elif menu_selection == 3:
				json_data = tmdb.Movies().popular(page=page, language=lang)
			elif menu_selection == 4:
				json_data = tmdb.Movies(ident).similar_movies(page=page, language=lang)
			elif menu_selection == 5:
				json_data = tmdb.Movies(ident).recommendations(page=page, language=lang)
			elif menu_selection == 6:
				json_data = tmdb.Movies().top_rated(page=page, language=lang)
			else:
				json_data = tmdb.Search().multi(query=text, language=lang)
			# {u'total_results': 0, u'total_pages': 0, u'page': 1, u'results': []}
			# logger.debug("json_data: %s", json_data)
		except Exception as e:
			logger.error("exception: %s", e)
			res = []
		else:
			results = {}
			self.parseJsonMultiple(results, json_data, ["total_pages", "results"])
			totalpages = results["total_pages"]
			for entry in results["results"]:
				logger.debug("entry: %s", entry)
				result = {}
				keys = ["media_type", "id", "title", "name", "release_date", "first_air_date", "poster_path", "backdrop_path", "profile_path"]
				self.parseJsonMultiple(result, entry, keys)

				media = result["media_type"]
				ident = result["id"]
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
				elif menu_selection:
					media = "movie"
					title = "%s (%s, %s)" % (title_movie, _("Movie"), date_movie[:4])
				else:
					media = ""

				if media == "person":
					cover_url = "http://image.tmdb.org/t/p/%s/%s" % (config.plugins.tmdb.cover_size.value, profile_path)
				else:
					cover_url = "http://image.tmdb.org/t/p/%s/%s" % (config.plugins.tmdb.cover_size.value, cover_path)
				backdrop_url = "http://image.tmdb.org/t/p/%s/%s" % (config.plugins.tmdb.backdrop_size.value, backdrop_path)

				logger.debug("ident: %s, title: %s, media: %s", ident, title, media)
				if ident and title and media:
					res.append(((title, ident, media, cover_url, backdrop_url), ))
		del json_data
		reactor.callFromThread(callback, totalpages, res)  # pylint: disable=E1101
