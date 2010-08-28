#!/usr/bin/env python
"""App Engine request handler for Readability API project.."""

__author__ = 'Anthony Lieuallen'
__copyright__ = 'Copyright 2010, Anthony Lieuallen'
__credits__ = ''
__license__ = 'GPLv3'
__version__ = '0.1'
__maintainer__ = __author__
__email__ = 'arantius@gmail.com'
__status__ = 'Prototype'  # 'Development'  # 'Production'

import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

import clean


class MainPage(webapp.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/html'
    path = os.path.join(os.path.dirname(__file__), 'templates/main.html')
    self.response.out.write(template.render(path, {}))


class CleanUrl(webapp.RequestHandler):
  def get(self):
    self.response.headers['Content-Type'] = 'text/html; charset=UTF-8'
    url = self.request.get('url') or self.request.get('link')
    self.response.out.write(clean.Clean(url))


def main():
  application = webapp.WSGIApplication(
      [('/', MainPage), ('/clean', CleanUrl)],
      debug='Development' in os.environ.get('SERVER_SOFTWARE', ''))
  run_wsgi_app(application)


if __name__ == '__main__':
  main()
