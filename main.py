#!/usr/bin/env python
"""App Engine request handler for Readability API project.

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

from email import utils as email_utils  # pylint: disable-msg=E0611,C6202
import os
import time

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import clean
import feed
import models
import util


class MainPage(webapp.RequestHandler):
  request = None
  response = None

  def get(self):
    self.response.headers['Content-Type'] = 'text/html'
    self.response.out.write(util.RenderTemplate('main.html'))


class CleanPage(webapp.RequestHandler):
  request = None
  response = None

  def get(self):
    url = self.request.get('url') or self.request.get('link')

    if url:
      output = clean.Clean(url)
    else:
      output = 'Provide "url" parameter!'

    self.response.headers['Content-Type'] = 'text/html; charset=UTF-8'
    self.response.headers['Cache-Control'] = 'max-age=3600'
    self.response.headers['Expires'] = email_utils.formatdate(
        timeval=time.time() + 3600, usegmt=True)
    self.response.out.write(output)


class CleanFeed(webapp.RequestHandler):
  request = None
  response = None

  def get(self):
    url = self.request.get('url') or self.request.get('link')
    include_original = self.request.get('include', None) == 'True'

    if not url:
      self.response.headers['Content-Type'] = 'text/plain; charset=UTF-8'
      self.response.out.write('Provide "url" parameter!')
      return

    feed_entity = models.Feed.get_by_key_name(url)
    if not feed_entity:
      feed_entity = feed.CreateFeed(url)
    self.response.headers['Content-Type'] = 'application/atom+xml; charset=UTF-8'
    self.response.out.write(feed.PrintFeed(feed_entity, include_original))


def main():
  application = webapp.WSGIApplication(
      [('/', MainPage), ('/page', CleanPage), ('/feed', CleanFeed),
       ('/clean', CleanPage),  # legacy
      ],
      debug=util.IS_DEV_APPSERVER)
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
