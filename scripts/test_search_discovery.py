"""Public route integration: discoverable pairs with reachable internal links."""
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urljoin

ROOT = Path(__file__).resolve().parent.parent
SITE = 'https://access.framontmanagement.com'
PAIRS = [
 ('/funds/', '/it/fondi/'), ('/amc/', '/it/amc/'),
 ('/eti/', '/it/eti/'), ('/deals/', '/it/deals/'),
 ('/amc/noctiluca-capital/', '/it/amc/noctiluca-capital/'),
 ('/amc/zalphyx-yield-strategies/', '/it/amc/zalphyx-yield-strategies/'),
 ('/eti/value-edge-snowwhite/', '/it/eti/value-edge-snowwhite/'),
]

class Links(HTMLParser):
 def __init__(self, text):
  super().__init__(); self.hrefs=[]; self.alternates={}; self.canonical=''
  self.feed(text)
 def handle_starttag(self, tag, attrs):
  a=dict(attrs)
  if tag=='a' and a.get('href'): self.hrefs.append(a['href'])
  if tag=='link' and a.get('rel')=='alternate': self.alternates[a.get('hreflang')]=a.get('href')
  if tag=='link' and a.get('rel')=='canonical': self.canonical=a.get('href')

def file_for(route):
 return ROOT / (route.lstrip('/') + 'index.html')

class DiscoveryTests(unittest.TestCase):
 def test_all_language_routes_are_registered_for_crawling(self):
  sitemap=ET.parse(ROOT/'sitemap.xml').getroot()
  entries={e.find('{*}loc').text:e for e in sitemap.findall('{*}url')}
  llms=(ROOT/'llms.txt').read_text()
  for en,it in PAIRS:
   for route in [en,it]:
    with self.subTest(route=route):
     url=SITE+route
     self.assertIn(url,entries)
     alternates={e.attrib['hreflang']:e.attrib['href'] for e in entries[url].findall('{*}link')}
     self.assertEqual(alternates.get('en'),SITE+en)
     self.assertEqual(alternates.get('it'),SITE+it)
     self.assertIn(url,llms)
 def test_language_links_are_reciprocal_and_all_local_destinations_exist(self):
  for en,it in PAIRS:
   for route,lang in [(en,'en'),(it,'it')]:
    with self.subTest(route=route):
     source=file_for(route)
     self.assertTrue(source.exists(),str(source))
     page=Links(source.read_text())
     self.assertEqual(page.canonical,SITE+route)
     self.assertEqual(page.alternates.get('en'),SITE+en)
     self.assertEqual(page.alternates.get('it'),SITE+it)
     for href in page.hrefs:
      url=urlsplit(urljoin(SITE+route,href))
      if url.netloc!=urlsplit(SITE).netloc or url.scheme not in ['http','https']: continue
      relative=url.path.lstrip('/')
      target=ROOT/(relative+'index.html' if not relative or relative.endswith('/') else relative)
      self.assertTrue(target.is_file(),f'{route} broken internal link {href}')
 def test_new_routes_are_reachable_from_homepage_through_public_anchors(self):
  visited=set()
  pending=['/']
  while pending:
   route=pending.pop()
   if route in visited: continue
   visited.add(route)
   file=ROOT/(route.lstrip('/')+'index.html' if route.endswith('/') else route.lstrip('/'))
   if not file.is_file() or file.suffix!='.html': continue
   for href in Links(file.read_text()).hrefs:
    if '{{' in href: continue
    target=urlsplit(urljoin(SITE+route,href))
    if target.netloc==urlsplit(SITE).netloc and target.scheme in ['http','https'] and not target.path.startswith('/preview/'):
     pending.append(target.path or '/')
  for en,it in PAIRS:
   self.assertIn(en,visited)
   self.assertIn(it,visited)

if __name__=='__main__': unittest.main()
