#!/usr/bin/env python
"""App Engine request handler for Readability API project.."""

"""
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

import logging
import os
import urllib

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine import runtime

import clean
import util

if util.IS_DEV_APPSERVER:
  logging.getLogger().setLevel(logging.DEBUG)
else:
  logging.getLogger().setLevel(logging.WARNING)


class MainPage(webapp.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/html'
    path = os.path.join(os.path.dirname(__file__), 'templates/main.html')
    self.response.out.write(template.render(path, {}))


class Clean(webapp.RequestHandler):
  def get(self):
    feed = self.request.get('feed')
    if feed:
      try:
        keep_contents = self.request.get('keep_contents', 'False') == 'True'
        clean_feed = clean.CleanFeed(feed, keep_contents)
        output = util.RenderTemplate('feed.xml', clean_feed)
      except runtime.DeadlineExceededError:
        # If we run out of time, we've probably processed (and cached) at least
        # one item.  Tell the client to redirect back here again, to resume
        # processing, and pick up after the cached items.
        self.response.clear()
        self.redirect('/clean?feed=' + urllib.quote(feed))
    else:
      url = self.request.get('url') or self.request.get('link')
      if url:
        output = clean.CleanUrl(url)
      else:
        output = 'Provide either "url" or "feed" parameters!'

    self.response.headers['Content-Type'] = 'text/html; charset=UTF-8'
    self.response.out.write(output)


def main():
  application = webapp.WSGIApplication(
      [('/', MainPage), ('/clean', Clean)],
      debug=util.IS_DEV_APPSERVER)
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
