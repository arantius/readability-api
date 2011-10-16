import os

from django import http
from django import shortcuts

FAVICON_PATH = os.path.join(
    os.path.dirname(__file__), 'static', 'favicon.ico')
ROBOTS_PATH = os.path.join(
    os.path.dirname(__file__), 'static', 'robots.txt')


def favicon(request):
  return http.HttpResponse(
      open(FAVICON_PATH).read(), 'image/vnd.microsoft.icon')


def home(request):
  return shortcuts.render_to_response('main.html')


def robots(request):
  return http.HttpResponse(
      open(ROBOTS_PATH).read(), 'text/plain')
