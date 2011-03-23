#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Cleaning wrapper.

Given a URL, first apply special cases.  Then try to fetch a feed of the
content, then try to directly handle the HTML.  Clean up all HTML where
appropriate.

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

import base64
import logging
import re
import urlparse

from third_party import BeautifulSoup
from third_party import hyphenate

import extract_content
import extract_feed
import util

_MAX_URL_DISPLAY_LEN = 60

RE_ALIGNED = re.compile(
    r'(?:_|\b)(?:align|float:\s*)?(left|right)(?:_|\b)', re.I)
STRIP_ATTRS = {
    'onblur': True,
    'onchange ': True,
    'onclick': True,
    'ondblclick': True,
    'onfocus': True,
    'onkeydown': True,
    'onkeypress': True,
    'onkeyup': True,
    'onload': True,
    'onmousedown': True,
    'onmousemove': True,
    'onmouseout': True,
    'onmouseover': True,
    'onmouseup': True,
    'onreset': True,
    'onselect': True,
    'onsubmit': True,
    'onunload': True,
    }
if not util.IS_DEV_APPSERVER:
  STRIP_ATTRS.update({
      'class': util.IS_DEV_APPSERVER,
      'id': util.IS_DEV_APPSERVER,
      'classid': True,
      'score': util.IS_DEV_APPSERVER,
      })


def Clean(url):
  truncate_url = url
  if len(url) > _MAX_URL_DISPLAY_LEN:
    truncate_url = url[0:60] + u'…'
  return u"Content extracted from: <a href='%s'>%s</a><hr>\n%s" % (
      url, truncate_url, _Clean(url))


def _Clean(url):
  """Clean the contents of a given URL to only the "readable part".

  Handle special cases like YouTube, PDF, images directly.  Delegate out to
  either extract content from the site's feed, or parse and clean the HTML.

  Args:
    url: String, the URL to the interesting content.

  Returns:
    String: HTML representing the "readable part".
  """
  # Handle de-facto standard "hash bang" URLs ( http://goo.gl/LNmg )
  url = url.replace('#!', '?_escaped_fragment_=')
  # Otherwise ignore fragments.
  url = re.sub(r'#.*', '', url)
  # And strip common tracking noise.
  url = re.sub(r'[?&]utm_[^&]+', '', url)

  match = re.search(r'^https?://docs.google.com.*cache:.*?:(.*?\.pdf)',
                    url, re.I)
  if match:
    url = match.group(1)
    if 'http' not in url:
      url = 'http://' + url

  match = re.search(r'^https?://docs.google.com.*docid=(.*?)(&|$)', url, re.I)
  if match:
    return util.RenderTemplate('google-docs.html', {'docid': match.group(1),
                                                    'url': url})

  if re.search(r'^http://www\.youtube\.com/watch', url, re.I):
    video_id = re.search(r'v=([^&]+)', url).group(1)
    return util.RenderTemplate('youtube.html', {'video_id': video_id})
  if re.search(r'^http://www\.trutv\.com/video', url, re.I):
    video_id = re.search(r'(/video[^?#]+).html', url).group(1)
    return util.RenderTemplate('trutv.html', {'video_id': video_id})
  elif re.search(r'\.pdf(\?|$)', url, re.I):
    return util.RenderTemplate('pdf.html', {'url': url})
  elif re.search(r'\.(gif|jpe?g|png)(\?|$)', url, re.I):
    return util.RenderTemplate('image.html', {'url': url})

  html, final_url, error = util.Fetch(url)
  if error:
    logging.error(error)
    return u'Download error: %s' % error

  note = ''
  try:
    extractor = extract_feed.FeedExtractor(
        url=url, final_url=final_url, html=html)
    note = 'cleaned feed'
    soup = extractor.soup
    tag = soup
  except extract_feed.RssError, e:
    note = 'cleaned content, %s, %s' % (e.__class__.__name__, e)
    soup, tag = extract_content.ExtractFromHtml(final_url, html)

  if util.IS_DEV_APPSERVER:
    logging.info(note)
  return _Munge(soup, tag, final_url)
if not util.IS_DEV_APPSERVER:
  Clean = util.Memoize('Clean_%s', 60*60*24)(Clean)  # pylint: disable-msg=C6409


def _FixUrls(parent, base_url):
  def _FixUrl(tag, attr):
    tag[attr] = urlparse.urljoin(base_url, tag[attr].strip())

  # pylint: disable-msg=C6405
  for tag in parent.findAll(href=True): _FixUrl(tag, 'href')
  if parent.has_key('href'): _FixUrl(parent, 'href')

  for tag in parent.findAll(src=True): _FixUrl(tag, 'src')
  if parent.has_key('src'): _FixUrl(parent, 'src')

  for tag in parent.findAll('object', data=True): _FixUrl(tag, 'data')
  if parent.name == 'object' and parent.has_key('data'): _FixUrl(parent, 'data')

  for tag in parent.findAll('param', attrs={'name': 'movie', 'value': True}):
    _FixUrl(tag, 'value')
  if parent.name == 'param' and parent['name'] == 'movie':
    _FixUrl(parent, 'value')


def _Munge(soup, tag, url):
  """Given a string of HTML content, munge it to be more pleasing."""
  # In certain failure cases, we'll still get a string.  Just use it.
  if isinstance(tag, basestring):
    return tag

  _MungeStripSiteSpecific(tag, url)
  _MungeStripBrsAfterPs(tag)
  _MungeStripAttrs(tag)
  _MungeStripRules(tag)
  _MungeStripEmpties(tag)
  tag = _MungeStripRootContainers(tag)

  _FixUrls(tag, url)
  _MungeImages(tag)
  _MungeHeaderDowngrade(tag)
  _MungeHyphenate(tag)
  _MungeNoscript(tag)
  tag = _MungeTransformEmbeds(soup, tag)

  # Serialize the tag, and apply full justification.
  if isinstance(tag, BeautifulSoup.BeautifulStoneSoup):
    # Wrap in a div, to have a tag to justify, if necessary.
    wrap = BeautifulSoup.Tag(soup, 'div')
    wrap.insert(0, tag)
    tag = wrap
  tag['style'] = 'text-align: justify;'

  return unicode(tag)


def _MungeHyphenate(root_tag):
  for text in root_tag.findAll(text=True):
    if text.findParent('pre'):
      continue
    text_parts = re.split(r'(&[^;]{2,6};)', text)
    new_text = []
    for text_part in text_parts:
      if not text_part:
        continue
      if '&' == text_part[0]:
        new_text.append(text_part)
      else:
        words = re.split(r'\s+', text_part)
        # ­ is a unicode soft hyphen here -- only two UTF-8 bytes, and
        # it doesn't clutter up the source view!
        words = [u'­'.join(hyphenate.hyphenate_word(word))
                 for word in words]
        new_text.append(' '.join(words))
    text.replaceWith(BeautifulSoup.NavigableString(''.join(new_text)))


def _MungeHeaderDowngrade(root_tag):
  for tag in root_tag.findAll(extract_content.TAG_NAMES_HEADER):
    tag.name = 'h%d' % min(6, int(tag.name[1]) + 2)


def _MungeImages(root_tag):
  # For all images:
  #  * If they have a style or class that implies floating, apply alignment.
  #  * If they are at the beginning of a paragraph, with text, apply alignment.
  for img in root_tag.findAll('img'):
    if img.has_key('align'):
      continue

    if img.has_key('style'):
      match = RE_ALIGNED.search(img['style'])
      if match:
        img['align'] = match.group(1)
        continue

    if img.has_key('class'):
      match = RE_ALIGNED.search(img['class'])
      if match:
        img['align'] = match.group(1)
        continue


def _MungeNoscript(root_tag):
  for tag in root_tag.findAll('noscript'):
    tag.name = 'div'


def _MungeStripAttrs(root_tag):
  for tag in root_tag.findAll(True):
    for attr in STRIP_ATTRS:
      del tag[attr]


def _MungeStripBrsAfterPs(root_tag):
  for tag in root_tag.findAll('p'):
    while True:
      next = tag.findNextSibling()
      if not next: break
      if next.name == 'br':
        next.extract()
      else:
        break


def _MungeStripEmpties(root_tag):
  strip_tags = (
      'a', 'center', 'div', 'li', 'ol', 'p', 'table', 'td', 'th', 'tr',
      'span', 'ul')

  def _StripIfEmpty(tag):
    if not tag or not tag.name or tag.name not in strip_tags:
      # We have to double check this, because of the parent recursion.
      return
    if tag.text.strip():
      return
    if tag.find(lambda tag: tag.name not in ('br', 'hr')):
      return
    parent = tag.parent
    tag.extract()
    # Also consider the parent, which might now be empty.
    _StripIfEmpty(parent)

  for tag in root_tag.findAll(strip_tags):
    _StripIfEmpty(tag)


def _MungeStripRootContainers(root_tag):
  # If this container holds only one tag, and empty text, choose that inner tag.
  child_tags = root_tag.findAll(True, recursive=False)
  if len(child_tags) != 1: return root_tag
  if ''.join(root_tag.findAll(text=True, recursive=False)).strip():
    return root_tag
  return _MungeStripRootContainers(child_tags[0])


def _MungeStripRules(root_tag):
  try:
    while root_tag.contents and root_tag.contents[-1].name == 'hr':
      root_tag.contents[-1].extract()
  except AttributeError:
    pass


def _MungeStripSiteSpecific(root_tag, url):
  if 'smashingmagazine.com' in url:
    for tag in root_tag.findAll('table', width='650'):
      tag.extract()


def _MungeTransformEmbeds(soup, root_tag):
  for tag in util.FindEmbeds(root_tag):
    try:
      w, h = util.TagSize(root_tag)
    except TypeError:
      w = 600
      h = 400
    link = BeautifulSoup.Tag(soup, 'a')
    link['href'] = 'data:text/html;base64,' + base64.b64encode(
        '<body style="margin:0;">%s</body>' % unicode(tag))
    link['rel'] = 'embedded_media'
    link['embed_width'] = w
    link['embed_height'] = h
    img = BeautifulSoup.Tag(soup, 'img')
    # http://readability-api.appspot.com
    img['src'] = '/embedded_media.png'
    img['width'] = '128'
    img['height'] = '128'
    link.insert(0, img)
    if tag == root_tag:
      return link
    tag.replaceWith(link)
  return root_tag
