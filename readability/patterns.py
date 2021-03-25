"""Pattern-based heuristics for BeautifulSoup objects.

Applies positive/negative scores to identify content, and completely removes
notes that are known to be unwanted.

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

import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from readability import util

# If one pattern matched this many tags, consider it a false positive, and
# subtract its points back out.
FALSE_POSITIVE_THRESHOLD = 15


def _ReAny(pattern):
  return re.compile(pattern, re.I)


def _ReWhole(pattern):
  return re.compile(r'(^|!!!)%s($|!!!)' % pattern, re.I)


def _ReWord(pattern):
  return re.compile(r'\b%s\b' % pattern, re.I)

ATTR_POINTS = (
    (-15, 'classid', _ReWhole(r'side')),
    (-15, 'classid', _ReWord(r'email')),
    (-15, 'classid', _ReWord(r'twitter')),
    (-10, 'classid', _ReWord(r'ghost')),
    (-10, 'classid', _ReWord(r'(item|panel) \d')),
    (-10, 'classid', _ReWord(r'overlay')),
    (-10, 'classid', _ReWord(r'print')),
    (-10, 'classid', _ReWord(r'topics?')),
    (-7, 'classid', _ReWhole(r'bio box')),
    (-5, 'classid', _ReAny(r'menu')),
    (-5, 'classid', _ReAny(r'social')),
    (-5, 'classid', _ReWord(r'ad')),
    (-5, 'classid', _ReWord(r'(?<!padding )bottom')),
    (-5, 'classid', _ReWord(r'dontprint')),
    (-5, 'classid', _ReWord(r'footer')),
    (-5, 'classid', _ReWord(r'global')),
    (-5, 'classid', _ReWord(r'hotspot')),  # tmz
    (-5, 'classid', _ReWord(r'icons')),
    (-5, 'classid', _ReWord(r'lightbox')),
    (-5, 'classid', _ReWord(r'links')),
    (-5, 'classid', _ReWord(r'more')),
    (-5, 'classid', _ReWord(r'post date')),
    (-5, 'classid', _ReWord(r'site')),
    (-5, 'rel', _ReWord(r'tag')),
    (-3, 'classid', _ReAny(r'embed')),  # usually "embed this" code
    (-2, 'classid', _ReWord(r'extras?')),
    (-2, 'classid', _ReWord(r'meta(data)?')),
    (2, 'classid', _ReWord(r'(?<!ads )main')),
    (2, 'classid', _ReWord(r'text')),
    (4, 'classid', _ReWord(r'article(?! tool)')),
    (5, 'classid', _ReAny(r'^article')),
    (5, 'classid', _ReAny(r'gallery(?! (caption|icon|item))')),
    (5, 'classid', _ReAny(r'photo')),
    (5, 'classid', _ReWhole(r'main(img)?')),
    (5, 'classid', _ReWhole(r'permalink')),
    (5, 'classid', _ReWhole(r'page')),
    (5, 'classid', _ReWhole(r'readme')),  # github
    (5, 'classid', _ReWord(r'body(text)?')),
    (5, 'classid', _ReWord(r'content')),
    (5, 'classid', _ReWord(r'primary column')),
    (5, 'classid', _ReWord(r'single')),
    (10, 'classid', _ReAny(r'^(article|kona) ?(body|copy)')),
    (10, 'classid', _ReWord(r'entry')),  # old.reddit.com
    (10, 'classid', _ReWord(r'usertext-body')),  # old.reddit.com
    (10, 'classid', _ReWhole(r'meme image holder')),
    (10, 'classid', _ReWhole(r'moreatboingboing')),
    (10, 'classid', _ReWhole(r'story')),
    (10, 'classid', _ReWord(r'(player|video)')),
    (10, 'classid', _ReWord(r'post(id)?[- ]?(\d+|body|content)?')),
    (10, 'classid', _ReWord(r'snap preview')),
    (10, 'classid', _ReWord(r'(?<!ad )wide')),
    (10, 'classid', _ReWhole(r'meat')),
    (10, 'classid', _ReWhole(r'post( \d+)?')),
    (12, 'classid', _ReWhole(r'article span image')),  # nytimes
    (12, 'classid', _ReWhole(r'h?entry( \d+)?')),
    (20, 'classid', _ReWhole(r'large image')),  # imgur.com
    (20, 'classid', _ReWhole(r'story(body|block)')),
    (20, 'classid', _ReWhole(r'player')),

    (-3, 'href', _ReAny(r'(delicious\.com|del\.icio\.us)/post')),
    (-3, 'href', _ReAny(r'(buzz\.yahoo|digg|mixx|propeller|reddit|stumbleupon)\.com/submit')),
    (-3, 'href', _ReAny(r'(facebook|linkedin)\.com/share')),
    (-3, 'href', _ReAny(r'(newsvine|yahoo)\.com/buzz')),
    (-3, 'href', _ReAny(r'^javascript:')),
    (-3, 'href', _ReAny(r'add(this|toany)\.com')),
    (-3, 'href', _ReAny(r'api\.tweetmeme\.com')),
    (-3, 'href', _ReAny(r'digg\.com/tools/diggthis')),
    (-3, 'href', _ReAny(r'fark\.com.*(farkit|new_url)')),
    (-3, 'href', _ReAny(r'furl.net/storeIt')),
    (-3, 'href', _ReAny(r'fusion\.google\.com/add')),
    (-3, 'href', _ReAny(r'google\.com/(bookmark|reader/link)')),
    (-3, 'href', _ReAny(r'myshare\.url\.com')),
    (-3, 'href', _ReAny(r'newsvine.com/_tools')),
    (-3, 'href', _ReAny(r'pheedo\.com')),
    (-3, 'href', _ReAny(r'twitter\.com/home\?status')),
    (-3, 'href', _ReWord(r'share')),
    (-3, 'href', _ReWord(r'sponsor')),
    (-2, 'href', _ReWord(r'feedads')),
    )
ATTR_STRIP = (
    # any '^topic' broke cracked.com
    ('classid', _ReAny(r'adsense')),
    ('classid', _ReAny(r'add(this|toany)')),
    ('classid', _ReWord(r'comment')),
    ('classid', _ReAny(r'disqus')),
    ('classid', _ReAny(r'functions')),
    ('classid', _ReAny(r'popular')),
    ('classid', _ReAny(r'^post_(\d+_)?info')),
    ('classid', _ReAny(r'reportabuse')),
    ('classid', _ReAny(r'share(bar|box|Post|this)')),
    ('classid', _ReAny(r'signin')),
    ('classid', _ReAny(r'text ad')),
    ('classid', _ReAny(r'(controls?|tool)(box|s)(?! container)')),

    # word 'share' breaks twitter
    # word 'head(er)?' breaks some sites that put _all_ content there
    # This categories target matches category classes on _the post_ container.
    #('classid', _ReWord(r'(in)?categor(ies|y)')),
    ('classid', _ReWord(r'(left|right)?nav(igation)?(?! wrap)')),
    ('classid', _ReWord(r'(post)?author(box)?|authdesc')),
    ('classid', _ReWord(r'ad( ?block|tag)')),
    ('classid', _ReWord(r'archive')),
    ('classid', _ReWord(r'byline')),
    ('classid', _ReWord(r'cnn( ftrcntnt|Footer)')),
    ('classid', _ReWord(r'cnn stry(btmcntnt|btntoolsbottom|cbftrtxt|lctcqrelt)')),
    ('classid', _ReWord(r'facebook like')),
    ('classid', _ReWord(r'(?<!non )foot(er)?(feature)?')),
    ('classid', _ReWord(r'(?<!overflow )hid(den|e)')),
    ('classid', _ReWord(r'horizontal posts')),  # mashable
    ('classid', _ReWord(r'icons')),
    ('classid', _ReWord(r'ilikethis')),
    ('classid', _ReWord(r'logo')),
    ('classid', _ReWord(r'metavalue')),
    ('classid', _ReWord(r'more articles')),
    ('classid', _ReWord(r'post labels?')),
    ('classid', _ReWord(r'post share')),
    ('classid', _ReWord(r'postmetadata')),
    ('classid', _ReWord(r'read more')),
    ('classid', _ReWord(r'related\d*')),
    ('classid', _ReWord(r'relatedtopics')),
    ('classid', _ReWord(r'replies')),
    ('classid', _ReWord(r'retweet')),
    ('classid', _ReWord(r'shop(box|rotator)')),
    ('classid', _ReWord(r'siteheader')),
    ('classid', _ReWord(r'snap nopreview')),
    ('classid', _ReWord(r'social')),
    ('classid', _ReWord(r'tag(ged|s| cloud)')),
    ('classid', _ReWord(r'talkback')),
    ('classid', _ReWord(r'wdt button')),
    ('classid', _ReWord(r'widget')),

    ('classid', _ReWhole(r'ads?( main)?')),
    ('classid', _ReWhole(r'article break')),
    ('classid', _ReWhole(r'article inline runaround left')),  # nytimes junk
    ('classid', _ReWhole(r'a(uthor )?info')),
    ('classid', _ReWhole(r'blippr nobr')),
    ('classid', _ReWhole(r'breadcrumb')),
    ('classid', _ReWhole(r'catsandtags')),
    ('classid', _ReWhole(r'dont print')),
    ('classid', _ReWhole(r'feedflare')),
    ('classid', _ReWhole(r'more stories')),
    ('classid', _ReWhole(r'pag(es|ination)')),
    ('classid', _ReWhole(r'post( date| info|ed on|edby|s)')),
    ('classid', _ReWhole(r'prevnext')),
    ('classid', _ReWhole(r'previously\d?|moreatboingboing')),  # boing boing
    ('classid', _ReWhole(r'promoColumn')),
    ('classid', _ReWhole(r'(recent|related) posts')),
    ('classid', _ReWhole(r'respon(d|ses)')),
    ('classid', _ReWhole(r'rightrail')),
    ('classid', _ReWhole(r'search(bar)?')),
    ('classid', _ReWhole(r'seealso')),
    ('classid', _ReWhole(r'sexy bookmarks')),
    ('classid', _ReWhole(r'share')),
    ('classid', _ReWhole(r'side(bar)?\d*')),  # word matches too much
    ('classid', _ReWhole(r'sociable')),
    ('classid', _ReWhole(r'story date')),
    ('classid', _ReWhole(r'notes( container)?')),  # tumblr comments
    ('classid', _ReWhole(r'post (details|notes)')),

    ('src', _ReAny(r'doubleclick\.net')),
    ('src', _ReAny(r'invitemedia\.com')),
    ('src', _ReAny(r'quantserve\.com')),
    ('src', _ReAny(r'leenks\.com/webmasters')),
    ('src', _ReAny(r'reddit\.com')),
    ('src', _ReAny(r'stumbleupon\.com')),
    ('src', _ReAny(r'1x1.trans.gif')),

    # Commonly indicates comments
    ('src', _ReWord(r'smilies')),

    ('id', _ReWhole(r'^[a-z0-9]{37}#[0-9]{16}$')),  # Plus comments
    ('classid', _ReWhole(r'vanilla credit|scribol')),  # comment systems

    ('style', _ReAny(r'display\s*:\s*none')),

    # QuickMeme filler.
    ('src', _ReAny(r'/social/qm.gif')),

    # Feed tracking noise.
    ('href', _ReWord(r'feedads')),
    ('href', _ReAny(r'^https?://feed[^/]+/(~.{1,3}|1\.0)/')),
    ('src', _ReAny(r'^https?://feed[^/]+/(~.{1,3}|1\.0)/')),
    )
RE_RELATED_HEADER = re.compile(
    r'\b('
    r'also on'
    r'|(for|read) more'
    r'|more.*(coverage|news|resources)'
    r'|most popular'
    r'|(popular|similar) (articles?|entries|posts?|stories)'
    r'|read more'
    r'|related'
    r'|see also'
    r'|suggested links'
    r')\b'
    r'|more\.\.\.', re.I)

DO_NOT_STRIP_TAGS = ('html', 'body')
STRIP_TAGS = (
    'head', 'iframe', 'link', 'meta', 'script', 'style', 'fb:share-button')


def _SeparateWords(s):
  """Turn camel case and underscore/hyphen word separators to spaces.

  e.g.
  fooBarBaz -> foo bar baz
  foo_bar_baz -> foo bar baz
  foo-bar-baz -> foo bar baz

  Args:
    s: Any string.

  Returns:
    String, as described.
  """
  s = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', s)
  s = re.sub('([a-z0-9])([A-Z])', r'\1 \2', s)
  s = s.replace('_', ' ')
  s = s.replace('-', ' ')
  return s.lower()


def _FindPreviousHeader(tag):
  # Find the "header" immediately previous to this tag.  Search among a few
  # possibilities for it.

  # If tag, and nothing else, is wrapped by e.g. a <div>, pop up.
  while len(tag.parent.findAll(name=True, recursive=False)) == 1:
    tag = tag.parent

  # First, try the immediately previous sibling node, skipping breaks.
  header = tag.findPreviousSibling(lambda tag: tag.name not in ('br', 'hr'))
  if header: return (header, header.getText(separator=' '))

  # Otherwise, look for text just before this tag.
  header = tag.findPreviousSiblings(text=True)
  if header: return (header[0], header[0])

  return (None, '')


def _IsLeafBlock(tag):
  if tag.name not in util.TAG_NAMES_BLOCK:
    return False
  if tag.find(name=util.TAG_NAMES_BLOCK):
    return False
  return True


def _IsList(tag):
  if tag.name == 'ul': return True
  if tag.name == 'ol': return True
  if 'blockquote' == tag.name:
    if re.search(r'(<br.*?> - .*){2,}', str(tag)):
      return True
  if 'center' == tag.name:
    tags_links = tag.findAll(name='a', recursive=False)
    if tags_links and len(tags_links) >= 8:
      return True
  return False


def _Score(tag, url, hit_counter):
  if tag.name == 'body': return

  if tag.name == 'article':
    util.ApplyScore(tag, 10, name='article_tag')
  elif tag.name == 'section':
    util.ApplyScore(tag, 1, name='section_tag')

  # Point patterns.
  for points, attr, pattern in ATTR_POINTS:
    if attr not in tag: continue
    if pattern.search(tag[attr]):
      parent_match = tag.parent and attr in tag.parent and (
          pattern.search(tag.parent[attr]))
      if not parent_match:
        util.ApplyScore(tag, points, name=attr)

      key = (points, attr, pattern.pattern)
      hit_counter.setdefault(key, [])
      hit_counter[key].append(tag)

  # Links.
  if tag.name == 'a' and tag.has_attr('href') and not tag.has_attr('score_href'):
    try:
      that_url = urllib.parse.urljoin(url, tag['href'])
    except ValueError:
      # Rare but possible for malformed documents.
      pass
    else:
      if url == that_url or url == urllib.parse.unquote(tag['href']):
        # Special case: score down AND strip links to this page.  (Including
        # "social media" links.)
        util.ApplyScore(tag, -1.5, name='self_link')
        util.Strip(tag, 'self link')
      # TODO: host name -> domain name
      elif urllib.parse.urlparse(url)[1] != urllib.parse.urlparse(that_url)[1]:
        # Score up links to _other_ domains.
        util.ApplyScore(tag, 1.0, name='out_link')

  # Blocks.
  if _IsLeafBlock(tag):
    # Length of stripped text, with all whitespace collapsed.
    text_len = _TextLen(tag)

    if text_len == 0:
      anchor = tag.find('a')
      img = tag.find('img')
      if anchor and not anchor.has_attr('score_out_link') and not img:
        util.ApplyScore(tag, -2, name='only_anchor')
    else:
      if text_len < 20 and tag.name != 'td':
        util.ApplyScore(tag, -0.75, name='short_text')
      if text_len > 50:
        util.ApplyScore(tag, 3, name='some_text')
      if text_len > 250:
        util.ApplyScore(tag, 4, name='more_text')

  # Images.
  if tag.name == 'img':
    util.ApplyScore(tag, 1.5, name='any_img')
    if tag.has_attr('alt') and len(tag['alt']) > 50:
      util.ApplyScore(tag, 2, name='img_alt')

    size = _TagSize(tag)
    if size is not None:
      if size <= 625:
        util.ApplyScore(tag, -1.5, name='tiny_img')
      if size >= 50000:
        util.ApplyScore(tag, 3, name='has_img')
      if size >= 250000:
        util.ApplyScore(tag, 4, name='big_img')


def _Strip(tag):
  if tag.name in DO_NOT_STRIP_TAGS:
    return False

  if tag.name in STRIP_TAGS:
    if tag.name == 'form':
      if 'aspnetForm' in [attr[1] for attr in tag.attrs]: return False
      if tag.find('input', id='__VIEWSTATE'): return False
    if tag.name == 'iframe' and tag.has_attr('score_has_embed'):
      return False
    if len(tag.text) > 2000: return False
    util.Strip(tag, 'STRIP_TAGS')
    return True

  # Strip "related" lists.
  if _IsList(tag):
    header, header_text = _FindPreviousHeader(tag)
    # Too-long text means this must not be a header, false positive!
    if len(header_text) < 100 and RE_RELATED_HEADER.search(header_text):
      util.Strip(tag, 'related tag')
      util.Strip(header, 'related header')
      return True

  for attr, pattern in ATTR_STRIP:
    if attr not in tag: continue
    if tag.has_attr(attr) and pattern.search(tag[attr]):
      if util.DEBUG:
        logging.info('Strip for %s: %s', attr, util.SoupTagOnly(tag))
        logging.info('  (Match %s against %s)',
                     pattern.search(tag[attr]).group(0), pattern.pattern)
      util.Strip(tag, 'strip attr ' + attr)
      return True

  return False


def _TagSize(tag):
  try:
    w, h = util.TagSize(tag)
  except TypeError:
    return None

  try:
    w = int(w)
    h = int(h)
  except ValueError:
    return None

  # Special case images that look small.
  if w < 25 or h < 25:
    return 1

  return int(w) * int(h)


def _TextLen(tag):
  """Length of this tag's text, without <a> nodes."""
  text_nodes = tag.findAll(text=True)
  text = [str(x).strip() for x in text_nodes
          if not x.findParent('a') and not x.findParent('script')]
  text = ''.join(text)
  text = re.sub(r'[ \t]+', ' ', text)
  text = re.sub(r'&[^;]{2,6};', '', text)
  return len(text)


def Process(root_tag, url, hit_counter=None):
  """Process an entire soup, without recursing into stripped nodes."""
  # Make a single "class and id" attribute that everything else can test.
  root_tag['classid'] = '!!!'.join([
      _SeparateWords(' '.join(root_tag.get('class', []))).strip(),
      _SeparateWords(root_tag.get('id', '')).strip()
      ]).strip('!')

  top_run = False
  if hit_counter is None:
    hit_counter = {}
    top_run = True

  _Score(root_tag, url, hit_counter)
  if _Strip(root_tag): return
  for tag in root_tag.findAll(True, recursive=False):
    Process(tag, url, hit_counter)

  # Look for too-frequently-matched false-positive patterns.
  if top_run:
    for key, tags in hit_counter.items():
      if len(tags) >= FALSE_POSITIVE_THRESHOLD:
        points, attr, unused_pattern = key
        if points < 0:
          # Only reverse false _positives_.  Negatives probably aren't false.
          continue
        logging.info(
            'Undoing %d points for %d tags, with %s matching %s',
            points, len(tags), attr, unused_pattern)
        for tag in tags:
          util.ApplyScore(tag, -1 * points, name=attr)
