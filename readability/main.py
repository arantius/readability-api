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

import email.utils
import re
import time

from django import http
from django.template import loader

from readability import clean
from readability import feed
from readability import models
from readability import util


def Main(request):
  tpl = template.loader.get_template('main.html')
  return http.HttpResponse(tpl.render({}, request))


def CleanPage(request):
  url = request.GET.get('url')

  if url:
    response = http.HttpResponse(clean.Clean(url))
    response['Content-Type'] = 'text/html; charset=UTF-8'
  else:
    response = http.HttpResponse('Provide "url" parameter!')
    response['Content-Type'] = 'text/plain; charset=UTF-8'

  response['Cache-Control'] = 'max-age=3600'
  response['Expires'] = email.utils.formatdate(
      timeval=time.time() + 3600, usegmt=True)
  return response


def CleanFeed(request):
  url = request.GET.get('url')
  include_original = request.GET.get('include', None) == 'True'

  if not url:
    response = http.HttpResponse('Provide "url" parameter!')
    response['Content-Type'] = 'text/plain; charset=UTF-8'
    return response

  url = re.sub(r'\?at=[^?&]+', '', url)
  try:
    feed_entity = models.Feed.objects.get(url=url)
  except models.Feed.DoesNotExist:
    feed_entity = feed.CreateFeed(url)

  response = http.HttpResponse(
      feed.RenderFeed(feed_entity, include_original))
  response['Content-Type'] = 'application/atom+xml; charset=UTF-8'
  return response
