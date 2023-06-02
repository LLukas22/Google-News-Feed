import urllib.parse
from lxml import etree
from lxml.etree import _Element
from datetime import datetime,date
from dateparser import parse
import asyncio
import logging
from typing import Optional
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
import aiohttp


GOOGLE_INTERNAL_URL = set(["https://news.google.com/__i/rss","https://news.google.com/rss"])   
BASE_URL = 'https://news.google.com/rss'
PARSER = etree.HTMLParser(recover=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
}

COOKIES = {
    'CONSENT': 'YES+cb.20220419-08-p0.cs+FX+111'
}

KNOWN_TOPICS={
    "BUSINESS":"CAAqKggKIiRDQkFTRlFvSUwyMHZNRGx6TVdZU0JXVnVMVlZUR2dKVlV5Z0FQAQ",
    "NATION":"CAAqKggKIiRDQkFTRlFvSUwyMHZNRGx6TVdZU0JXVnVMVlZUR2dKVlV5Z0FQAQ",
    "WORLD":"CAAqJggKIiBDQkFTRWdvSkwyMHZNRGxqTjNjd0VnVmxiaTFWVXlnQVAB",
    "TECHNOLOGY":"CAAqKggKIiRDQkFTRlFvSUwyMHZNRGx1YlY4U0JXVnVMVlZUR2dKVlV5Z0FQAQ",
    "ENTERTAINMENT":"CAAqKggKIiRDQkFTRlFvSUwyMHZNREpxYW5RU0JXVnVMVlZUR2dKVlV5Z0FQAQ",
    "SCIENCE":"CAAqKggKIiRDQkFTRlFvSUwyMHZNREpxYW5RU0JXVnVMVlZUR2dKVlV5Z0FQAQ",
    "SPORTS":"CAAqKggKIiRDQkFTRlFvSUwyMHZNRFp1ZEdvU0JXVnVMVlZUR2dKVlV5Z0FQAQ",
    "HEALTH":"CAAqJQgKIh9DQkFTRVFvSUwyMHZNR3QwTlRFU0JXVnVMVlZUS0FBUAE"
}
    
@dataclass
class NewsItem(object):
    title:Optional[str]=None
    link:Optional[str]=None
    pubDate:Optional[datetime]=None
    description:Optional[str]=None
    source:Optional[str]=None

    def __repr__(self) -> str:
        return f'{self.title}'
    
    @property
    def is_internal_google_link(self)->bool:
        for internal_link in GOOGLE_INTERNAL_URL:
            if self.link.startswith(internal_link):
                return True
        return False
    
class GoogleNewsFeed:
    def __init__(self,language:str='en',country:str='US',client:Optional[requests.Session]=None,resolve_internal_links:bool=True,run_async:bool=True)->None:
        self.language = language.lower()
        self.country = country.upper()
        if client:
            self.client = client
        else:
            self.client = requests.Session()
            self.client.headers.update(HEADERS)
            self.client.cookies.update(COOKIES)

        self.resolve_internal_links = resolve_internal_links
        self.run_async = run_async
        
        
    @staticmethod
    def _build_ceid(country:str,language:str)->str:
        return f'hl={language}-{country}&gl={country}&ceid={country}:{language}'
    
    @staticmethod
    def _build_query(query:str)->str:
        return urllib.parse.quote(query, safe='')
    
    @staticmethod
    def _build_query_url(query:str,country:str,language:str,before:date=None,after:date=None,when:str=None)->str:
        base_ure = f"{BASE_URL}/search?q="
        
        query = GoogleNewsFeed._build_query(query)
        
        time_restrictions = []
        if when:
            time_restrictions.append(f"when:{when}")
        else:
            if before:
                time_restrictions.append(f"before:{before.isoformat()}")
            if after:
                time_restrictions.append(f"after:{after.isoformat()}")
        
        if len(time_restrictions) > 0:
            return f"{base_ure}{query}+{'+'.join(time_restrictions)}&{GoogleNewsFeed._build_ceid(country,language)}"
        else:
            return f"{base_ure}{query}&{GoogleNewsFeed._build_ceid(country,language)}"
      
      
    @staticmethod
    def _parse_item(item:_Element)->NewsItem:
        parsed_item = NewsItem()
        for element in item.getchildren():
            match element.tag:
                case 'title':
                    parsed_item.title = element.text
                case 'link':
                    parsed_item.link = element.tail
                case 'pubdate':
                    parsed_item.pubDate = parse(element.text)
                case 'description':
                    parsed_item.description = list(etree.fromstring(element.text,parser=PARSER).iter('a'))[0].text
                case 'source':
                    parsed_item.source = element.text
                          
        return parsed_item
                    
        
        
    @staticmethod
    def _parse_feed(content:str)->list[NewsItem]:
        root = etree.fromstring(content,parser=PARSER)
        
        parsed_items = []
        for item in root.iter('item'):
            try:
                parsed_items.append(GoogleNewsFeed._parse_item(item))
            except Exception as e:
                logging.debug(f"Failed to parse item: {item}! Exception: {e}")
            
        return parsed_items
        
    async def _async_resolve_internal_links(self,items:list[NewsItem])->list[NewsItem]:
        async with aiohttp.ClientSession() as session:
            session.headers.update(HEADERS)
            session.cookie_jar.update_cookies(COOKIES)
            for item in items:
                try:
                    if item.is_internal_google_link:
                        async with session.get(item.link) as response:
                            content = await response.text()
                            if content:
                                soup = BeautifulSoup(content, 'html.parser')
                                item.link = soup.a['href']
                                del soup
                except:
                    logging.debug(f"Failed to resolve internal link: {item.link}")
        return items
    
    def _resolve_internal_links(self,items:list[NewsItem])->list[NewsItem]:
        for item in items:
            try:
                if item.is_internal_google_link:
                    response = self.client.get(item.link)
                    if response.text:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        item.link = soup.a['href']
                        del soup
            except:
                    logging.debug(f"Failed to resolve internal link: {item.link}")
        return items
        
    def _get_feed(self,url:str)->list[NewsItem]:
        result = self.client.get(url)
        if result.status_code == 200:
            items =  GoogleNewsFeed._parse_feed(result.content)
            if self.resolve_internal_links:
                if self.run_async:
                    items = asyncio.run(self._async_resolve_internal_links(items))
                else:
                    items = self._resolve_internal_links(items)
            return items
        else:
            raise Exception(f"Error fetching feed: {url}")
        
    def query_topic(self,topic:str)->list[NewsItem]:
        if topic.upper() in KNOWN_TOPICS:
            topic = KNOWN_TOPICS[topic.upper()]
            
        url = f"{BASE_URL}/topics/{topic}?{GoogleNewsFeed._build_ceid(self.country,self.language)}"
        return self._get_feed(url)
        
    def top_headlines(self)->list[NewsItem]:
        url = f"{BASE_URL}?{GoogleNewsFeed._build_ceid(self.country,self.language)}"
        return self._get_feed(url)
        
    def query(self,query:str,before:date=None,after:date=None,when:str=None)->list[NewsItem]:
        """
        For more information on the parameters, see:
        https://newscatcherapi.com/blog/google-news-rss-search-parameters-the-missing-documentaiton
        """
        url = GoogleNewsFeed._build_query_url(query,self.country,self.language,before,after,when)
        return self._get_feed(url)
            
    @classmethod
    def known_topics()->list[str]:
        return KNOWN_TOPICS.keys()
    
    @classmethod
    def get_topic_hash(topic:str)->str|None:
        if topic.upper() in KNOWN_TOPICS:
            return KNOWN_TOPICS[topic.upper()]
        return None
             
if __name__ == "__main__":
    gnf = GoogleNewsFeed()
    news = gnf.query("apple")
    print(news)
        
        
        