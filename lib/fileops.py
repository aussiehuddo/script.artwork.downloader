#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2011-2014 Martijn Kaijser
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

#import modules
import os
import socket
import urllib
import urllib2
import xbmc
import xbmcvfs
import lib.common

### import libraries
from lib.script_exceptions import *
from lib.gui import dialog_msg
from lib.utils import log
from traceback import print_exc
from urllib2 import HTTPError, URLError

### get addon info
ADDON         = lib.common.ADDON
PROFILE_PATH  = lib.common.PROFILE_PATH
localize      = lib.common.localize

tempdir = os.path.join(PROFILE_PATH, 'temp')
THUMBS_CACHE_PATH = xbmc.translatePath( "special://profile/Thumbnails/Video" )
### adjust default timeout to stop script hanging
timeout = 10
socket.setdefaulttimeout(timeout)

class fileops:
    """
    This class handles all types of file operations needed by
    script.extrafanartdownloader (creating directories, downloading
    files, copying files etc.)
    """

    def __init__(self):
        log("Setting up fileops")
        self._exists = lambda path: xbmcvfs.exists(path)
        self._rmdir = lambda path: xbmcvfs.rmdir(path)
        self._mkdir = lambda path: xbmcvfs.mkdir(path)
        self._delete = lambda path: xbmcvfs.delete(path)

        self.downloadcount = 0
        if not self._exists(tempdir):
            if not self._exists(PROFILE_PATH):
                if not self._mkdir(PROFILE_PATH):
                    raise CreateDirectoryError(PROFILE_PATH)
            if not self._mkdir(tempdir):
                raise CreateDirectoryError(tempdir)
        
    def _copy(self, source, target):
        return xbmcvfs.copy(source.encode("utf-8"), target.encode("utf-8"))

    ### Delete file from all targetdirs
    def _delete_file_in_dirs(self, filename, targetdirs, reason, media_name = '' ):
        isdeleted = False
        for targetdir in targetdirs:
            path = os.path.join(targetdir, filename)
            if self._exists(path):
                self._delete(path)
                log("[%s] Deleted (%s): %s" % (media_name, reason, path))
                isdeleted = True
        if not isdeleted:
            log("[%s] Ignoring (%s): %s" % (media_name, reason, filename))

    # copy file from temp to final location
    def _copyfile(self, sourcepath, targetpath, media_name = ''):
        targetdir = os.path.dirname(targetpath).encode("utf-8")
        if not self._exists(targetdir):
            if not self._mkdir(targetdir):
                raise CreateDirectoryError(targetdir)
        if not self._copy(sourcepath, targetpath):
            raise CopyError(targetpath)
        else:
            log("[%s] Copied successfully: %s" % (media_name, targetpath) )

    # download file
    def _downloadfile(self, item, mode = ""):
        try:
            temppath = os.path.join(tempdir, item['filename'])
            tempfile = open(temppath, "wb")
            response = urllib2.urlopen(item['url'])
            tempfile.write(response.read())
            tempfile.close()
            response.close()
        except HTTPError, e:
            if e.code == 404:
                raise HTTP404Error(item['url'])
            else:
                raise DownloadError(str(e))
        except URLError:
            raise HTTPTimeout(item['url'])
        except socket.timeout, e:
            raise HTTPTimeout(item['url'])
        except Exception, e:
            log(str(e), xbmc.LOGNOTICE)
        else:
            log("[%s] Downloaded: %s" % (item['media_name'], item['filename']))
            self.downloadcount += 1
            for targetdir in item['targetdirs']:
                #targetpath = os.path.join(urllib.url2pathname(targetdir).replace('|',':'), filename)
                targetpath = os.path.join(targetdir, item['filename'])
                self._copyfile(temppath, targetpath, item['media_name'])
                
def cleanup():
    if xbmcvfs.exists(tempdir):
        dialog_msg('updateBG', percentage = 100,
                   line1 = localize(32005),
                   background =  ADDON.getSetting('background'))
        log('Cleaning up temp files')
        for x in os.listdir(tempdir):
            tempfile = os.path.join(tempdir, x)
            xbmcvfs.delete(tempfile)
            if xbmcvfs.exists(tempfile):
                log('Error deleting temp file: %s' % tempfile, xbmc.LOGERROR)
        xbmcvfs.rmdir(tempdir)
        if xbmcvfs.exists(tempdir):
            log('Error deleting temp directory: %s' % tempdir, xbmc.LOGERROR)
        else:
            log('Deleted temp directory: %s' % tempdir)