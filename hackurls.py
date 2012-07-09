#!/usr/bin/env python
# http://www.hackurls.com engine
# by Claudio Santini - vuotomeccanico on gmail 
# http://theorymatters.wordpress.com

import feedparser
from RSS import CollectionChannel, TrackingChannel, ns # decode RSS from hackaday
import codecs
from BeautifulSoup import BeautifulSoup, Tag, NavigableString, BeautifulStoneSoup
import Image
import httplib2
import time
import os 
import shutil
import re
import Image, ImageDraw, ImageFont
import hashlib
from datetime import date, timedelta

# Order matters
from django.core.management import setup_environ
from dj import settings
setup_environ(settings)

#from dj.link.models import Link
from dj.nerd.models import Nerd
from django.template import Template, Context

DEBUG = False
FORCE_CACHE = False
DOWNLOAD_TIMEOUT = 5
MAX_IMAGES = 80
MAX_TITLE_LEN = 70
MAX_DESC_LEN = 200

DEPLOY_DIRECTORY = 'pub/'
THUMBS_DIRECTORY = DEPLOY_DIRECTORY+'imgs/thumbs'
NERDS_DIRECTORY = DEPLOY_DIRECTORY+'imgs/nerds'
THUMBS_LINK_DIRECTORY = 'imgs/thumbs'
NERDS_LINK_DIRECTORY = 'imgs/nerds'

cache = httplib2.FileCache("hackurls_cache")

def cut_title(string):
	if len(string) > MAX_TITLE_LEN:
		return string[0:MAX_TITLE_LEN]+"..."
	else:
		return string

def cut_description(string):
	if len(string) > MAX_DESC_LEN:
		return string[0:MAX_DESC_LEN]+"..."
	else:
		return string
		
def cut_all_descriptions(entries):
	for entry in entries:
		 entry.description = cut_description(entry.description)
	return entries
		
"""Removes thumbnails older than a quarter hour"""
def clean_thumbs_directory():
	now = time.time()
	for f in os.listdir(THUMBS_DIRECTORY):
		filename = os.path.join(THUMBS_DIRECTORY, f)
		last_edit = os.stat(filename).st_mtime
		if now - last_edit > 60*15:
			os.unlink(filename)

"""Download (and cache) <url> file to imgs/thumbs/. Returns saved file name. """
def download_img(url, file_name):
	print 'downloading ' + url
	try:
		h = httplib2.Http("hackurls_cache", timeout=10)
		resp, content = h.request(url)	
		f = open(file_name, "w")
		f.write(content) 
		f.close()
	except Error, e:
		print 'Error downloading img: ' + e 
	return file_name
		
"""Resize an image (rewriting it)"""
def thumbnail(file, x=120, y=100):
	print "thumbnailing " + file
	try:
		image = Image.open(file)
		image.thumbnail([x, y], Image.ANTIALIAS)
		image.save(file, image.format)
	except IOError, e:
		print 'IOError: ' + e
	return file
	
"""Download ad resize an img from a given URL"""
def download_and_thumbnail(url, x=120, y=100):
	format = url.rsplit('.', 1)[1]		# www.site.com/path/img.jpg -> .jpg
	format = format.split('?', 1)[0] 	# could be: .jpg?w=100&y=200&...
	hashfun = hashlib.md5()
	hashfun.update(url)
	file_name = os.path.join(THUMBS_DIRECTORY, str(hashfun.hexdigest()) + '.' + format)
	if not os.path.exists(file_name):
		download_img(url, file_name)
		thumb_name = thumbnail(file_name, x=x, y=y)
		thumb_name = thumb_name[len(DEPLOY_DIRECTORY):]	# cut off starting 'pub/'
		return thumb_name
	thumb_name = file_name[len(DEPLOY_DIRECTORY):]	# cut off starting 'pub/'
	return thumb_name

def download_feed(url, file_name):
	content = None
	if FORCE_CACHE:
		content = cache.get(url)
		print "using cache"
	else:
		try:
			print "downloading " + url
			h = httplib2.Http("hackurls_cache", timeout=10)
			resp, content = h.request(url)
		except httplib2.ServerNotFoundError:
			return None
				
	file_name = os.path.join("feeds", file_name)
	f = open(file_name, "w")
	f.write(content) 
	f.close()
	return file_name	

def get_feed(url, file_name):
	if DEBUG:
		file_name = 'feeds/'+file_name
	else:
		try:
			file_name = download_feed(url, file_name)
		except Exception, e:
			print e
			return []
	rss = feedparser.parse(file_name)
	return rss.entries

"""If the link is an image, puts a thumbnail of the picture inside the description"""	
def description_thumbs(entries):
	for entry in entries:
		if entry.link.endswith('.jpg') or entry.link.endswith('.jpeg') or entry.link.endswith('.png'):
			thumb = download_and_thumbnail(entry.link, x=200, y=200)			
			entry.description = '<img src=\''+ thumb +'\'><br/>' + entry.description
		elif entry.link.startswith('http://imgur.com/'):
			# TODO: add .gif support 
			if entry.link.endswith('.jpg') or entry.link.endswith('.png'):
				print entry.link
				thumb = download_and_thumbnail(entry.link+'.jpg')
				entry.description = '<img src=\''+ thumb +'\'><br/>' + entry.description
	return entries
	
def images_from_html(html):
	soup = BeautifulSoup(html)	
	tags = soup.findAll('img')
#	for img in images_from_html():
#		print img['src']
	return tags
	
def links_from_html(html):
	# TODO: Use regex here please
	soup = BeautifulSoup(html)
	tags = soup.findAll('a')
	return tags

def remove_html_tags(data):
    p = re.compile(r'<.*?>')
    return p.sub('', data)

def get_hackernews_feed():
	entries = get_feed("http://news.ycombinator.com/rss", "hackernews")
	for entry in entries:
		entry.comments_link = entry.comments
	return entries

#def get_hackaday_feed_feedparser_version():
#	valid = []
#	entries = get_feed("http://hackaday.com/feed/", "hackaday")	
##	for i in range(len(entries)):
##		entries[i].description = entries[i].content[0].value
#	for entry in entries:
#		try:
#			img_tags = images_from_html(entry.content[0].value)
#			img_src = img_tags[0]['src']
#			if not DEBUG:
#				img_name = download_img(img_src)
#				thumb = thumbnail("imgs/thumbs/"+img_name)
#				entry.img = thumb
#			entry.description = remove_html_tags(entry.description)
#			valid.append(entry)
#		except IOError:
#			# don't care about links with pic we can't thumbnail
#			continue
#	return valid

def get_hackaday_feed():
	valid = []
	tc = TrackingChannel()
	tc.parse("http://hackaday.com/feed/")
	items = tc.listItems()
	
	for i in range(len(items)):
		entry = {}
		item = tc.getItem(items[i])
		entry['title'] = cut_title(item.get((ns.rss10, "title")))
		entry['description'] = item.get((ns.rss10, "description"))
		entry['link'] = item.get((ns.rss10, "link"))
		encoded = item.get((u'http://purl.org/rss/1.0/modules/content/', u'encoded'))
		try:
			img_tags = images_from_html(encoded)
			img_src = img_tags[0]['src']
			if not DEBUG:
				thumb = download_and_thumbnail(img_src)
				entry['img'] = thumb
			#entry.description = remove_html_tags(entry.description)
			valid.append(entry)
		except IOError:
			# don't care about links with pic we can't thumbnail
			continue
	return valid

def get_engadget_feed():
	entries = get_feed('http://www.engadget.com/rss.xml', 'engadget')
	
	for entry in entries:
		addr = None
		imgs = images_from_html(entry.description)
		for img in imgs:
			addr = img['src']
			if addr != None:
				break
		if addr == None: 
			continue
		thumb = download_and_thumbnail(addr)
		entry.description = remove_html_tags(entry.description)
		entry['img'] = thumb
	return entries
	
def get_reddit_description(entry, comment_page):
	print "download/parse ", comment_page
	html = cache.get(comment_page)
	if html == None:
		h = httplib2.Http("hackurls_cache", timeout=DOWNLOAD_TIMEOUT)
		resp, html = h.request(comment_page)
	try :
		soup = BeautifulSoup(html)
		# we only parse a piece of the page, it could be very long because of comments:
		if len(soup) > 24000:
			soup = soup[0:23999] 
		
		# <form class="form-t3_ak2b8igo"><div>...
		#form = soup.find('form', {'id': 'form-t3_ak2b8igo'})
		mds = soup.findAll('div', {'class': 'md'})
		try: 
			entry.description = cut_description(mds[2])
			return True
		except IndexError as detail:
			print 'index error ', detail
			return False
	except UnicodeEncodeError:
		return False
	
def get_reddit_like_feed(url, name, find_description=True):
	entries = get_feed(url, name)
	for entry in entries:
		entry.comments_link = entry.link
		tags = links_from_html(entry.summary_detail.value)
#		print entry.summary_detail.value
		found = False
		for tag in tags:
			if not tag['href'].startswith("http://www.reddit.com/"):
				entry.link = tag['href']
				entry.description = ''
				found = True
				break
		if find_description and not found and not DEBUG:
			if not get_reddit_description(entry, entry.link):
				entry.description = ''
	return entries

def get_reddit_feed():
	return get_reddit_like_feed("http://www.reddit.com/.rss", "reddit")

def get_proggit_feed():
	return get_reddit_like_feed("http://www.reddit.com/r/programming/.rss", "proggit")
	
def get_reddit_videos():
	feeds = []
	feeds.append(get_reddit_like_feed('http://www.reddit.com/r/geek/.rss', 'r_geek', find_description=False))
	feeds.append(get_reddit_like_feed('http://www.reddit.com/r/technology/.rss', 'r_technology', False))
	feeds.append(get_reddit_like_feed('http://www.reddit.com/r/science/.rss', 'r_science', False))
	feeds.append(get_reddit_like_feed('http://www.reddit.com/r/scifi/.rss', 'r_scifi', False))
	feeds.append(get_reddit_like_feed('http://www.reddit.com/r/gaming/.rss', 'r_gaming', False))
	
	videos = []
	for feed in feeds:
		for entry in feed:
			if entry.link.startswith('http://www.youtube.com/watch?v='):
				# extract code from http://www.youtube.com/watch?v=3yaY98GTCYM#t=3m45s
				youtube_code = entry.link.split('http://www.youtube.com/watch?v=')[1]
				youtube_code = youtube_code.split('#')[0].split('&')[0]
				entry['thumb'] = 'http://i2.ytimg.com/vi/' + youtube_code + '/default.jpg'
				entry.title = cut_title(entry.title)
				videos.append(entry)
	return videos
	
def get_slashdot_feed():
	entries = get_feed("http://rss.slashdot.org/Slashdot/slashdot", "slashdot");
	for entry in entries:
		entry.description = remove_html_tags(entry.description) 
	return entries	
	
def get_nerd_of_the_day():

	now = date.today()
	one_day = timedelta(days=1)

	def new_nerd():
		nerd = Nerd.objects.filter(seen=False, published=False)[0]
		if nerd == None:
			print 'No new nerds'
			return None
		nerd.published = True
		nerd.publish_date = now
		thumbnail(os.path.join(NERDS_DIRECTORY, nerd.img), x=320, y=320)
		nerd.save()
		return nerd

	nerds = Nerd.objects.filter(published=True)
	nerd = None
	
	if len(nerds) == 0:
		nerd = new_nerd()	
	else:
	 	nerd = nerds[0]
	 	if now - one_day > nerd.publish_date:
			nerd = new_nerd()
		
	nerd.img = NERDS_LINK_DIRECTORY + '/' + nerd.img
	return nerd
	
#def draw_logo(text, font_size=200):
#	font = ImageFont.truetype("liberation.ttf", font_size)
#	img = Image.new("1", (1,1))	# temp to get font total size
#	draw = ImageDraw.Draw(img)
#	size = draw.textsize(text, font=font)
#	img = Image.new("RGB", size, 0)
#	draw = ImageDraw.Draw(img)
#	draw.text((0,0), text, font=font, fill=1)
#	img.show()

# Download feeds
clean_thumbs_directory()
hackernews = get_hackernews_feed()
reddit = description_thumbs(get_reddit_feed())
proggit = get_proggit_feed()
dzone = get_feed("http://www.dzone.com/links/feed/frontpage/rss.xml", "dzone")
slashdot = get_slashdot_feed()
techmeme = get_feed("http://www.techmeme.com/index.xml", "techmeme")
engadget = get_engadget_feed()
hackaday = get_hackaday_feed()
videos = get_reddit_videos()

# Renders HTML page
template_file = open('template.html')
t = Template(template_file.read())
template_file.close()
context_table = {
	'hackernews': hackernews, 
	'reddit': reddit,
	'proggit': proggit, 
	'hackaday': hackaday[0:12], 
	'dzone': dzone,
	'slashdot': slashdot,
	'techmeme': techmeme,
	#'engadget': engadget[0:14],
	'videos': videos,
	'nerd': get_nerd_of_the_day(),
	'logos': '5'
}
context = Context(context_table)
html = t.render(context)
page_file = codecs.open(DEPLOY_DIRECTORY+'/index_n.html','w','utf8')
page_file.write(html)
page_file.close()

# Render ASCII page
template_file = open('ascii_template')
t = Template(template_file.read())
template_file.close()
del context_table['nerd']
del context_table['logos']
context_table['context_table'] = context_table
context = Context(context_table)
text = t.render(context)
text = BeautifulStoneSoup(text, convertEntities=BeautifulStoneSoup.HTML_ENTITIES).contents[0]
ascii_file = codecs.open(DEPLOY_DIRECTORY+'/ascii','w','utf8')
ascii_file.write(text)
ascii_file.close()


'''One day I could need something else...'''
def get_job_feed(url, file_name):
	return cut_all_descriptions(get_feed(url, file_name))

# hackwage, hackurls.com/jobs
python = get_job_feed("http://www.python.org/community/jobs/jobs.rss", "python")
ruby_on_rails = get_job_feed("http://www.rorjobs.com/a/jbb/find-jobs-rss?sb=1&sbo=1", "ruby_on_rails")
django = get_job_feed("http://djangogigs.com/feeds/gigs/", "django")
signals = get_job_feed("http://jobs.37signals.com/categories/2/jobs.rss", "signals")
crunchboard = get_job_feed("http://feeds.feedburner.com/CrunchboardJobs?format=xml", "crunch_board")
reddit_jobs = get_job_feed("http://www.redditjobs.com/Rss/HomePage.aspx", "reddit_jobs")
startuply = get_job_feed("http://www.startuply.com/Rss/HomePage.aspx", "startuply")

template_file = open('templatejobs.html')
t = Template(template_file.read())
template_file.close()
context_table = {
	'python': python,
	'ruby_on_rails': ruby_on_rails,
	'django': django,
	'signals': signals,
	'crunchboard': crunchboard,
	'reddit_jobs': reddit_jobs,
	'startuply': startuply
}
context = Context(context_table)
html = t.render(context)
page_file = codecs.open('pub/jobs.html','w','utf8')
page_file.write(html)
page_file.close()
