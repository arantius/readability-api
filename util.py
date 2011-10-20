import Cookie
import hashlib
import logging
import re
import urllib2
import urlparse

import cssutils
from django.core.cache import cache
from lxml import cssselect

import settings

EVENT_ATTRS = (
    'onblur', 'onchange ', 'onclick', 'ondblclick', 'onfocus', 'onkeydown',
    'onkeypress', 'onkeyup', 'onload', 'onmousedown', 'onmousemove',
    'onmouseout', 'onmouseover', 'onmouseup', 'onreset', 'onselect', 'onsubmit',
    'onunload',
    )
NAMESPACE_RE = "http://exslt.org/regular-expressions"
OK_EMPTY_TAGS = (
    'br', 'embed', 'hr', 'iframe', 'img', 'input', 'object', 'param',
    )
STOP_WORDS = set([
    "able", "about", "above", "abroad", "according", "accordingly", "across", "actually", "adj", "after", "afterwards", "again", "against", "ago", "ahead", "ain't", "all", "allow", "allows", "almost", "alone", "along", "alongside", "already", "also", "although", "always", "am", "amid", "amidst", "among", "amongst", "an", "and", "another", "any", "anybody", "anyhow", "anyone", "anything", "anyway", "anyways", "anywhere", "apart", "appear", "appreciate", "appropriate", "are", "aren't", "around", "as", "a's", "aside", "ask", "asking", "associated", "at", "available", "away", "awfully", "back", "backward", "backwards", "be", "became", "because", "become", "becomes", "becoming", "been", "before", "beforehand", "begin", "behind", "being", "believe", "below", "beside", "besides", "best", "better", "between", "beyond", "both", "brief", "but", "by", "came", "can", "cannot", "cant", "can't", "caption", "cause", "causes", "certain", "certainly", "changes", "clearly", "c'mon", "co", "co.", "com", "come", "comes", "concerning", "consequently", "consider", "considering", "contain", "containing", "contains", "corresponding", "could", "couldn't", "course", "c's", "currently", "dare", "daren't", "definitely", "described", "despite", "did", "didn't", "different", "directly", "do", "does", "doesn't", "doing", "done", "don't", "down", "downwards", "during", "each", "edu", "eg", "eight", "eighty", "either", "else", "elsewhere", "end", "ending", "enough", "entirely", "especially", "et", "etc", "even", "ever", "evermore", "every", "everybody", "everyone", "everything", "everywhere", "ex", "exactly", "example", "except", "fairly", "far", "farther", "few", "fewer", "fifth", "first", "five", "followed", "following", "follows", "for", "forever", "former", "formerly", "forth", "forward", "found", "four", "from", "further", "furthermore", "get", "gets", "getting", "given", "gives", "go", "goes", "going", "gone", "got", "gotten", "greetings", "had", "hadn't", "half", "happens", "hardly", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "hello", "help", "hence", "her", "here", "hereafter", "hereby", "herein", "here's", "hereupon", "hers", "herself", "he's", "hi", "him", "himself", "his", "hither", "hopefully", "how", "howbeit", "however", "hundred", "i'd", "ie", "if", "ignored", "i'll", "i'm", "immediate", "in", "inasmuch", "inc", "inc.", "indeed", "indicate", "indicated", "indicates", "inner", "inside", "insofar", "instead", "into", "inward", "is", "isn't", "it", "it'd", "it'll", "its", "it's", "itself", "i've", "just", "k", "keep", "keeps", "kept", "know", "known", "knows", "last", "lately", "later", "latter", "latterly", "least", "less", "lest", "let", "let's", "like", "liked", "likely", "likewise", "little", "look", "looking", "looks", "low", "lower", "ltd", "made", "mainly", "make", "makes", "many", "may", "maybe", "mayn't", "me", "mean", "meantime", "meanwhile", "merely", "might", "mightn't", "mine", "minus", "miss", "more", "moreover", "most", "mostly", "mr", "mrs", "much", "must", "mustn't", "my", "myself", "name", "namely", "nd", "near", "nearly", "necessary", "need", "needn't", "needs", "neither", "never", "neverf", "neverless", "nevertheless", "new", "next", "nine", "ninety", "no", "nobody", "non", "none", "nonetheless", "noone", "no-one", "nor", "normally", "not", "nothing", "notwithstanding", "novel", "now", "nowhere", "obviously", "of", "off", "often", "oh", "ok", "okay", "old", "on", "once", "one", "ones", "one's", "only", "onto", "opposite", "or", "other", "others", "otherwise", "ought", "oughtn't", "our", "ours", "ourselves", "out", "outside", "over", "overall", "own", "particular", "particularly", "past", "per", "perhaps", "placed", "please", "plus", "possible", "presumably", "probably", "provided", "provides", "que", "quite", "qv", "rather", "rd", "re", "really", "reasonably", "recent", "recently", "regarding", "regardless", "regards", "relatively", "respectively", "right", "round", "said", "same", "saw", "say", "saying", "says", "second", "secondly", "see", "seeing", "seem", "seemed", "seeming", "seems", "seen", "self", "selves", "sensible", "sent", "serious", "seriously", "seven", "several", "shall", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "since", "six", "so", "some", "somebody", "someday", "somehow", "someone", "something", "sometime", "sometimes", "somewhat", "somewhere", "soon", "sorry", "specified", "specify", "specifying", "still", "sub", "such", "sup", "sure", "take", "taken", "taking", "tell", "tends", "th", "than", "thank", "thanks", "thanx", "that", "that'll", "thats", "that's", "that've", "the", "their", "theirs", "them", "themselves", "then", "thence", "there", "thereafter", "thereby", "there'd", "therefore", "therein", "there'll", "there're", "theres", "there's", "thereupon", "there've", "these", "they", "they'd", "they'll", "they're", "they've", "thing", "things", "think", "third", "thirty", "this", "thorough", "thoroughly", "those", "though", "three", "through", "throughout", "thru", "thus", "till", "to", "together", "too", "took", "toward", "towards", "tried", "tries", "truly", "try", "trying", "t's", "twice", "two", "un", "under", "underneath", "undoing", "unfortunately", "unless", "unlike", "unlikely", "until", "unto", "up", "upon", "upwards", "us", "use", "used", "useful", "uses", "using", "usually", "v", "value", "various", "versus", "very", "via", "viz", "vs", "want", "wants", "was", "wasn't", "way", "we", "we'd", "welcome", "well", "we'll", "went", "were", "we're", "weren't", "we've", "what", "whatever", "what'll", "what's", "what've", "when", "whence", "whenever", "where", "whereafter", "whereas", "whereby", "wherein", "where's", "whereupon", "wherever", "whether", "which", "whichever", "while", "whilst", "whither", "who", "who'd", "whoever", "whole", "who'll", "whom", "whomever", "who's", "whose", "why", "will", "willing", "wish", "with", "within", "without", "wonder", "won't", "would", "wouldn't", "yes", "yet", "you", "you'd", "you'll", "your", "you're", "yours", "yourself", "yourselves", "you've", "zero",
    ])


def applyCss(doc, url):
  affected_els = []
  # Apply all CSS into style attributes.  (Before stripping it.)
  for el in doc.xpath('//link[@rel="stylesheet"]'):
    css_url = urlparse.urljoin(url, el.attrib['href'])
    sheet = CSS_PARSER.parseUrl(css_url, media=el.attrib.get('media', None))
    if sheet:
      affected_els += applyCssRules(
          sheet.cssRules, doc, css_url, media=el.attrib.get('media', None))
  for el in doc.xpath('//style'):
    sheet = CSS_PARSER.parseString(el.text, href=url)
    if sheet:
      affected_els += applyCssRules(sheet.cssRules, doc, url)

  def collapseStyle(t):
    """Turn one .items() from a .style dict into a CSS declaration."""
    p, v = t
    _, v = v
    return '%s:%s' % (p, v)
  for el in set(affected_els):
    if 'style' in el.attrib:
      try:
        attr_decl = cssutils.css.CSSStyleDeclaration(
            el.attrib.get('style', None))
      except:
        pass
      else:
        cssutils.replaceUrls(attr_decl, lambda u: urlparse.urljoin(css_url, u))
        for decl in attr_decl:
          el.style[decl.name] = 99999, decl.propertyValue.cssText
    el.attrib['style'] = ';'.join(map(collapseStyle, el.style.items()))


def applyCssRules(rules, doc, base_url, media=None):
  affected_els = []
  for rule in rules:
    if isinstance(rule, cssutils.css.CSSCharsetRule):
      pass
    elif isinstance(rule, cssutils.css.CSSComment):
      pass
    elif isinstance(rule, cssutils.css.CSSFontFaceRule):
      pass
    elif isinstance(rule, cssutils.css.CSSImportRule):
      pass
      # TODO: Make this work.
#      css_url = urlparse.urljoin(base_url, rule.href)
#      sheet = CSS_PARSER.parseUrl(css_url, media=media)
#      if sheet:
#        affected_els += applyCssRules(
#            sheet.cssRules, doc, css_url, media=media)
    elif isinstance(rule, cssutils.css.CSSMediaRule):
      applyCssRules(
          rule.cssRules, doc, base_url,
          media=('print' in rule.media) and 'print' or 'screen')
    elif isinstance(rule, cssutils.css.CSSStyleRule):
      decl_dict = {}
      for decl in rule.style:
        decl_dict[decl.name] = decl.propertyValue.cssText

      # For every selector in this rule ...
      for selector in rule.selectorList:
        try:
          sel = cssselect.CSSSelector(selector.selectorText)
        except: # cssselect.ExpressionError, cssselect.SelectorSyntaxError:
          continue
        sel_specificity = sum(selector.specificity)
        if media == 'print':
          sel_specificity += 100

        # For every element that matches this selector ...
        for el in sel(doc):
          if el.tag == 'param':
            continue

          try:
            getattr(el, 'style')
          except AttributeError:
            el.style = {}

          # For every property in this declaration ...
          for prop, val in decl_dict.items():
            el_prop = el.style.get(prop)
            # If the property doesn't yet exist, or doeswith lower specificity..
            if not el_prop or el_prop[0] <= sel_specificity:
              # Use the new value.
              el.style[prop] = sel_specificity, val
              affected_els.append(el)
    else:
      print 'Unknown rule:', type(rule), rule
  return affected_els


def cacheKey(key):
  """The DB table has a 255 char limit, make sure that is not exceeded."""
  if len(key) < 255:
    return key
  else:
    return key[0:200] + hashlib.sha1(key[200:]).hexdigest()


def cleanUrl(url):
  # Handle de-facto standard "hash bang" URLs ( http://goo.gl/LNmg )
  url = url.replace('#!', '?_escaped_fragment_=')
  # Strip tracking noise.
  url = re.sub(r'utm_[a-z]+=[^&]+(&?)', r'\1', url)
  # Strip possibly left over query string delimiters.
  url = re.sub(r'[?&]+$', '', url)
  return url.strip()


def fetchCss(url):
  """Fetcher which uses getUrl() to provide cssutils' required format."""
  content, _, _ = getUrl(url)
  return None, content


def fixUrls(parent, base_url):
  def _fixUrl(el, attr):
    el.attrib[attr] = urlparse.urljoin(base_url, el.attrib[attr].strip())

  for attr in ('background', 'href', 'src'):
    for el in parent.xpath('//*[@%s]' % attr): _fixUrl(el, attr)
    if parent.attrib.has_key(attr): _fixUrl(parent, attr)

  for el in parent.xpath('//object[@data]'): _fixUrl(el, 'data')
  if parent.tag == 'object' and el.attrib.has_key('data'):
    _fixUrl(parent, 'data')

  for el in parent.xpath('//param[@name="movie" and @value]'):
    _fixUrl(el, 'value')


def getUrl(orig_url):
  cache_key = cacheKey('url:' + cleanUrl(orig_url))
  result = cache.get(cache_key)
  if result:
    return result

  cookie = Cookie.SimpleCookie()
  redirect_limit = 10
  redirects = 0
  url = orig_url
  while url and redirects < redirect_limit:
    redirects += 1
    url = cleanUrl(url)
    if settings.DEBUG:
      logging.info('Fetching: %s', url)
    final_url = url

    request = urllib2.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:7.0.1) Gecko/20100101 Firefox/7.0.1',
        })
    response = urllib2.urlopen(request, timeout=5)
    content = response.read()

    mime_type = response.headers.get('Content-type')
    cookie.load(response.headers.get('Set-Cookie', ''))
    previous_url = url
    url = response.headers.get('Location')
    if url:
      url = urlparse.urljoin(previous_url, url)
  final_url = urlparse.urljoin(orig_url, final_url)

  result = (content, mime_type, final_url)
  cache.set(cache_key, result)
  return result


def preCleanDoc(doc, url):
  applyCss(doc, url)

  # TODO: Manually apply e.g. SWFObject?

  # Strip elements by simple rules.
  for el in doc.xpath('//comment() | //script | //style | //head'):
    if el.getparent() is not None: el.drop_tree()

  # Strip elements by style.
  for el in doc.xpath(
      "//*[re:test(@style, 'display\s*:\s*none|position\s*:\s*fixed|visibility\s*:\s*hidden', 'i')]",
      namespaces={'re': NAMESPACE_RE}):
    el.drop_tree()

  # Strip attributes from all elements.
  for el in doc.xpath('//*'):
    for attr in EVENT_ATTRS:
      try:
        del el.attrib[attr]
      except KeyError:
        # Attribute doesn't exist.
        pass


def postCleanDoc(doc):
  # Strip empty nodes.
  found_empty = False
  for el in doc.xpath('//*[not(node())]'):
    if el.tag in OK_EMPTY_TAGS: continue
    if el.getparent() is not None:
      found_empty = True
      el.drop_tree()
  if found_empty:
    # Recurse in case removed nodes' parents are now empty.
    return postCleanDoc(doc)

  # In case we're finishing training, clear out those nodes.
  for el in doc.xpath('//*[@train = "remove"]'):
    if el.getparent() is not None:
      el.drop_tree()

  # Flatten a tree of nodes with only one child.
  while len(doc.getchildren()) == 1:
    doc = doc.getchildren()[0]

  # Selected containers often have fixed widths and float, so drop styles.
  try:
    del doc.attrib['style']
  except KeyError:
    pass

  return doc


def _wordFilter(w):
  if w in STOP_WORDS: return False
  if len(w) < 2: return False
  if not re.match(r'[a-z]', w, re.I): return False
  return True


def _wordMunge(w):
  return re.sub(r'[!-@\[-`]+$', '', w)  # Strip trailing punctuation.


def words(s):
  """Turn various strings to lists of words.

  Splits on non-whitespace separators e.g.
    fooBarBaz -> ['foo', 'bar', 'baz']
    foo_bar_baz -> ['foo', 'bar', 'baz']
    foo-bar-baz -> ['foo', 'bar', 'baz']
  Also, slashes, qmarks, ampersands, etc. (words in URL parts).

  Also eliminates stop words.

  Args:
    s: Any string.

  Returns:
    set() of of unique strings, as described.
  """
  if not s: return set()
  s = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', s)
  s = re.sub('([a-z0-9])([A-Z])', r'\1 \2', s)
  s = re.sub('[-_/?&=.:@\s]+', ' ', s)
  if not s: return set()
  all_words = s.lower().strip().split(' ')
  all_words = filter(_wordFilter, all_words)
  all_words = map(_wordMunge, all_words)
  return set(all_words) - STOP_WORDS


# Constants depending on things defined above.
CSS_PARSER = cssutils.CSSParser(fetcher=fetchCss, loglevel=logging.CRITICAL)
