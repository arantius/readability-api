import os

from django import http
from django import shortcuts
from lxml import html

import util

FAVICON_PATH = os.path.join(
    os.path.dirname(__file__), 'static', 'favicon.ico')
ROBOTS_PATH = os.path.join(
    os.path.dirname(__file__), 'static', 'robots.txt')

def cleanPage(request):
  url = request.GET['url']
  content = util.getUrl(url)
  doc = html.fromstring(content)

  # Always unconditionally remove these elements.
  for el in doc.xpath('//head | //script | //style'):
    el.drop_tree()

  # Build "classid" values, counting occurrances as we go.
  word_freq = {}
  for el in doc.xpath('//*[@class or @id]'):
    words = set(
        util.words(el.attrib.get('class', '')) +
        util.words(el.attrib.get('id', ''))
        )
    for word in words:
      word_freq.setdefault(word, 0)
      word_freq[word] += 1
    el.attrib['classid'] = ' '.join(words).strip()

  for x in sorted([(v, k) for (k, v) in word_freq.items()]):
    print x

  # Add a base href.
  base = html.Element('base', href=url)
  doc.insert(0, base)

  # Turn it back into HTML!
  return http.HttpResponse(html.tostring(doc, encoding=unicode))

def favicon(request):
  return http.HttpResponse(
      open(FAVICON_PATH).read(), 'image/vnd.microsoft.icon')

def home(request):
  return shortcuts.render_to_response('main.html')

def robots(request):
  return http.HttpResponse(
      open(ROBOTS_PATH).read(), 'text/plain')
