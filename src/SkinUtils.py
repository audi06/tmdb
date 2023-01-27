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
from enigma import getDesktop
from Tools.Directories import resolveFilename, SCOPE_SKIN, SCOPE_CURRENT_SKIN, SCOPE_PLUGINS
from skin import loadSkin, loadSingleSkinData, dom_skins
from .Debug import logger
from .Version import ID, PLUGIN


def getSkinName(skin_name):
	width = getDesktop(0).size().width()
	if width != 1920:
		skin_name = "NoSupport"
	return ID + skin_name


def getScalingFactor():
	return {"HD": 0.66, "FHD": 1, "WQHD": 1.33}[getResolution()]


def getResolution():
	height = getDesktop(0).size().height()
	logger.info("height: %s", height)
	resolution = ""
	if height > 576:
		resolution = "HD"
	if height > 720:
		resolution = "FHD"
	if height > 1080:
		resolution = "WQHD"
	logger.debug("resolution: %s", resolution)
	return resolution


def getSkinPath(file_name, size=0):
	logger.debug("file_name: %s, size: %s", file_name, size)
	resolution = getResolution()
	skin_path = resolveFilename(SCOPE_CURRENT_SKIN, PLUGIN + "/skin/" + resolution + "/" + file_name)
	# logger.debug("skin_path1: %s", skin_path)
	if not os.path.exists(skin_path):
		skin_path = resolveFilename(SCOPE_SKIN, "Default-FHD/" + PLUGIN + "/skin/" + resolution + "/" + file_name)
		# logger.debug("skin_path2: %s", skin_path)
		if not os.path.exists(skin_path):
			skin_path = resolveFilename(SCOPE_PLUGINS, "Extensions/" + PLUGIN + "/skin/" + resolution + "/" + file_name)
			# logger.debug("skin_path3: %s", skin_path)
			if not os.path.exists(skin_path):
				skin_path = resolveFilename(SCOPE_SKIN, resolution + "/" + file_name)
				# logger.debug("skin_path4: %s", skin_path)
	logger.debug("skin_path: %s", skin_path)
	return skin_path


def initPluginSkinPath():
	default_skin = resolveFilename(SCOPE_SKIN, "Default-FHD/" + PLUGIN)
	current_skin = resolveFilename(SCOPE_CURRENT_SKIN, PLUGIN)
	plugin_skin = resolveFilename(SCOPE_PLUGINS, "Extensions/" + PLUGIN)
	if not os.path.exists(plugin_skin):
		plugin_skin = resolveFilename(SCOPE_PLUGINS, "SystemPlugins/" + PLUGIN)
	logger.info("current_skin: %s", current_skin)
	logger.info("default_skin: %s", default_skin)
	logger.info("plugin_skin: %s", plugin_skin)
	if not os.path.isdir(default_skin):
		logger.info("%s > %s", default_skin, plugin_skin)
		os.symlink(plugin_skin, default_skin)


def loadPluginSkin(skin_file):
	loadSkin(getSkinPath(skin_file), "")
	path, dom_skin = dom_skins[-1:][0]
	loadSingleSkinData(getDesktop(0), dom_skin, path)
