from bs4 import BeautifulSoup
import requests
from feedgen.feed import FeedGenerator
import re
import boto3
import os
import json

os.environ["AWS_CONFIG_FILE"] = "/home/private/nbn-host-feed/config"

# Set up feed
nbn_host_profile = 'https://newbooksnetwork.com/hosts/profile/112f8337-847b-411d-b237-0171df1fb217'
feed_url='https://nbn-host-feed.s3.eu-west-2.amazonaws.com/miranda.xml'
fg = FeedGenerator()
fg.title('Miranda Melcher on New Books Network')
fg.logo('https://nbn-host-feed.s3.eu-west-2.amazonaws.com/miranda-nbn.png')
fg.author( name='Miranda Melcher')
fg.contributor( name='Miranda Melcher')
fg.description(description='Miranda\'s interviews with authors from across New Books Network channels.')
fg.id(nbn_host_profile)
fg.ttl(ttl=1440)
fg.link(href=feed_url,rel='self')
fg.link(href=nbn_host_profile,rel='alternate')
fg.language('en')
fg.load_extension('base')	


# Get episode page links
page = requests.get(nbn_host_profile)
soup = BeautifulSoup(page.text, 'html.parser')
episode_cards=soup.find_all('div', class_='episode-card')
episode_links=[]

for each in episode_cards:
	anchors=each.find_all('a')
	episode_links.append((anchors[1].get('href')))

# Get content from episode page and add episode to feed
for each in episode_links:
	fe = fg.add_entry()
	fe.id(each)
	fe.guid(each,permalink=True)
	fe.link(href=each,rel='alternate')
	fe.link(href=feed_url,rel='self')
	fe.author(name='Miranda Melcher')
	fe.contributor( name='Miranda Melcher')
	page = requests.get(each)
	soup = BeautifulSoup(page.text, 'html.parser')
	iframes = soup.find_all('iframe')
	megaphone_url = iframes[1].get('src')
	megaphone_id = re.search('(NBN)\d+', megaphone_url)
	mp3_url = 'https://dcs.megaphone.fm/' + megaphone_id.group() + '.mp3'
	fe.enclosure(url=mp3_url,type='audio/mpeg') # set podcast audio url
	book_title = soup.find('h1')
	book_author = soup.find('h4')
	fe.title(book_title.string + ' (' + book_author.string + ')') # set episode title
	description = soup.find('div', class_='episode')
	fe.description(description=str(description),isSummary=True)
	fe.content(content=str(description),type='text/html')

	
	script_tags = soup.find_all('script')
	pub_date_container=json.loads(script_tags[3].string)
	fe.published(pub_date_container['@graph'][0]['datePublished'])


rssfeed  = fg.rss_str(pretty=True) # Get the RSS feed as string
fg.rss_file('miranda.xml') # Write the RSS feed to a file


# Send file to S3

file_name=os.path.basename('/home/private/nbn-host-feed/miranda.xml')
bucket='nbn-host-feed'

s3 = boto3.client('s3')

s3.upload_file(file_name, bucket, file_name, ExtraArgs={'ContentType': 'application/rss+xml'})