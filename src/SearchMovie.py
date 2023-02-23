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


class SearchMovie(Json):
	def __init__(self):
		Json.__init__(self)

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
