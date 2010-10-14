#!/usr/bin/env python
"""Views for scheduled tasks for Readability API project.

--------------------------------------------------------------------------------

Readability API - Clean up pages and feeds to be readable.
Copyright (C) 2010  Anthony Lieuallen

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

import models
import util


class CleanStaleEntries(webapp.RequestHandler):
  request = None
  response = None

  def get(self):
    for feed in models.Feed.all():
      db.delete(feed.stale_entries)


def main():
  application = webapp.WSGIApplication(
      [('/crons/clean_stale_entries', CleanStaleEntries),
      ],
      debug=util.IS_DEV_APPSERVER)
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
