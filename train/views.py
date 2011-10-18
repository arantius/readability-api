import urllib

from django import http
from django import shortcuts
import lxml.html

from train import models

import util


def _gatherFacets(doc):
  facets = {}
  def countFacet(kind, data, is_spam):
    k = (kind, data)
    facets.setdefault(k, {'spam': 0, 'ham': 0})
    facets[k][is_spam and 'spam' or 'ham'] += 1

  for el in doc.xpath('//*'):
    is_spam = False
    status_el = el
    while status_el is not None:
      if 'train' in status_el.attrib:
        is_spam = status_el.attrib['train'] == 'remove'
        break
      status_el = status_el.getparent()

    text = ' '.join(el.xpath('./text()'))
    words = util.words(text)

    countFacet('tag_name', el.tag, is_spam)

    if el.tag in util.OK_EMPTY_TAGS:
      pass
    else:
      countFacet('num_text_words', len(words), is_spam)
      for word in words:
        countFacet('text_word', word, is_spam)

    for attr in ('alt', 'class', 'href', 'id', 'src'):
      for word in util.words(urllib.unquote(el.attrib.get(attr, ''))):
        countFacet(attr + '_word', word, is_spam)


  return facets

def data(request):
  try:
    models.Page.objects.filter(url=request.POST['url']).get()
  except models.Page.DoesNotExist:
    pass
  else:
    return http.HttpResponse('Page already trained.')

  page = models.Page(url=request.POST['url'])
  page.save()

  doc = lxml.html.fromstring(request.POST['html'])

  # TODO: Later, flatten these facets by kind/data.
  facets = _gatherFacets(doc)
  for (kind, data), counts in facets.iteritems():
    facet = models.Facet(
        kind=kind, ham_count=counts['ham'], spam_count=counts['spam'])
    if isinstance(data, basestring):
      facet.data_char = data
    else:
      facet.data_int = data
    facet.save()

  # Clean for display.
  doc = util.postCleanDoc(doc)

  facets_display = facets.items()
  facets_display.sort(key=lambda x: x[1], reverse=True)

  return shortcuts.render_to_response('train-data.html', {
      'content': lxml.html.tostring(doc),
      'facets': facets_display,
      })


def form(request):
  url = request.GET['url']
  content, mime_type, final_url = util.getUrl(url)
  if 'text/html' not in mime_type:
    content = 'Unsupported mime type.'
  else:
    doc = lxml.html.fromstring(content)

    util.preCleanDoc(doc, final_url)
    util.fixUrls(doc, final_url)
    doc = util.postCleanDoc(doc)

    content = ''.join([
        lxml.html.tostring(child)
        for child in doc.body.iterchildren()])

  return shortcuts.render_to_response('train-form.html', {
      'content': content,
      'final_url': final_url,
      'url': url,
      })
