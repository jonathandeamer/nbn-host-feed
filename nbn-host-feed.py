from bs4 import BeautifulSoup
import requests
from feedgen.feed import FeedGenerator
import re
import boto3
import os
import json

# Set the AWS configuration file environment variable
os.environ["AWS_CONFIG_FILE"] = "/home/private/nbn-host-feed/config"

# Initialize RSS feed settings
nbn_host_profile = 'https://newbooksnetwork.com/hosts/profile/112f8337-847b-411d-b237-0171df1fb217'
feed_url='https://nbn-host-feed.s3.eu-west-2.amazonaws.com/miranda.xml'

# Create an instance of FeedGenerator
fg = FeedGenerator()

# Set properties for the feed
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

# Start a requests session for persistent HTTP connections
with requests.Session() as s:
    # Get the host profile page
    page = s.get(nbn_host_profile, timeout=5)
    if page.status_code != 200:
        print(f"Failed to get page: {nbn_host_profile}")
    else:
        # Parse the HTML of the host profile page
        soup = BeautifulSoup(page.text, 'lxml')
        # Find all episode cards
        episode_cards=soup.find_all('div', class_='episode-card')
        episode_links=[]

        # For each episode card, find the episode URL and add it to the list
        for each in episode_cards:
            anchors=each.find_all('a')
            url = anchors[1].get('href')
            # Correct the URL encoding
            correct_url = url.encode('latin-1').decode('utf-8')
            episode_links.append(correct_url)

        # For each episode URL (in reverse order), fetch the episode details and add an entry to the feed
        for each in reversed(episode_links):
            # Initialize a new feed entry
            fe = fg.add_entry()
            fe.id(each)
            fe.guid(each,permalink=True)
            fe.link(href=each,rel='alternate')
            fe.link(href=feed_url,rel='self')
            fe.author(name='Miranda Melcher')
            fe.contributor( name='Miranda Melcher')
            print(each)
            # Get the episode page
            page = s.get(each, timeout=5)
            if page.status_code != 200:
                print(f"Failed to get page: {each}")
                continue
            try:
                # Parse the HTML of the episode page
                soup = BeautifulSoup(page.text, 'lxml')
            except Exception as e:
                print(f"Failed to parse page: {each}. Error: {str(e)}")
                continue

            # Extract the necessary details from the episode page
            iframes = soup.find_all('iframe')
            megaphone_url = iframes[1].get('src')
            print(megaphone_url)
            megaphone_id = re.search('([A-Z])\w+', megaphone_url)
            print(megaphone_id)
            mp3_url = 'https://dcs.megaphone.fm/' + megaphone_id.group() + '.mp3'
            # Set the podcast audio URL
            fe.enclosure(url=mp3_url,type='audio/mpeg')
            book_title = soup.find('h1')
            book_author = soup.find('h4')
            # Set the episode title
            fe.title(book_title.string + ' (' + book_author.string + ')')
            description = soup.find('div', class_='episode')
            # Set the episode description and content
            fe.description(description=str(description),isSummary=True)
            fe.content(content=str(description),type='text/html')

            # Extract the publication date from the script tags
            script_tags = soup.find_all('script')
            pub_date_container=json.loads(script_tags[3].string)
            fe.published(pub_date_container['@graph'][0]['datePublished'])

# Get the RSS feed as a string and write it to an XML file
rssfeed  = fg.rss_str(pretty=True)
fg.rss_file('/home/private/nbn-host-feed/miranda.xml')

# Prepare to upload the XML file to S3
file_name='/home/private/nbn-host-feed/miranda.xml'
object_name=os.path.basename('/home/private/nbn-host-feed/miranda.xml')
bucket='nbn-host-feed'

# Create an S3 client
s3 = boto3.client('s3')

# Upload the XML file to S3
s3.upload_file(file_name, bucket, object_name, ExtraArgs={'ContentType': 'application/rss+xml'})
