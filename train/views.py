from django import http
from django import shortcuts
import lxml.html

import util


def data(request):
  doc = lxml.html.fromstring(request.POST['html'])

  trained_data = []
  for el in doc.xpath('//*'):
    is_spam = False
    status_el = el
    while status_el is not None:
      if 'train' in status_el.attrib:
        is_spam = status_el.attrib['train'] == 'remove'
        break
      status_el = status_el.getparent()
    text = ' '.join(el.xpath('./text()'))

    data = {
        'el': el,
        'facets': [],
        'is_spam': is_spam,
        'text': text,
        'words': util.words(text),
        }
    trained_data.append(data)

  return shortcuts.render_to_response('train-data.html', {
      'content': request.POST['html'],
      'trained_data': trained_data,
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
    util.postCleanDoc(doc)

    content = ''.join([
        lxml.html.tostring(child)
        for child in doc.body.iterchildren()])

  return shortcuts.render_to_response('train-form.html', {
      'content': content,
      'final_url': final_url,
      'url': url,
      })
