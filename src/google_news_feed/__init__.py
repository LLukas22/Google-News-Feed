import urllib.parse
import httpx
from lxml import etree
from lxml.etree import _Element
from datetime import datetime,date
from dateparser import parse
import asyncio
import logging


GOOGLE_INTERNAL_URL = "https://news.google.com/__i/rss"    
BASE_URL = 'https://news.google.com/rss'
PARSER = etree.HTMLParser(recover=True)
MOVED_STATUS_CODE = 301

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
    
class NewsItem(object):
    title:str
    link:str
    pubDate:datetime
    description:str
    source:str
    def __init__(self,title:str=None,link:str=None,pubDate:datetime=None,description:str=None,source:str=None) -> None:
        self.title = title
        self.link = link
        self.pubDate = pubDate
        self.description = description
        self.source = source
        
    def __repr__(self) -> str:
        return f'{self.title}'
    
    @property
    def is_google_internal_link(self)->bool:
        return self.link.startswith(GOOGLE_INTERNAL_URL)
    
class GoogleNewsFeed:
    def __init__(self,language:str='en',country:str='US',client:httpx.Client=None,resolve_internal_links:bool=True,run_async:bool=True)->None:
        self.language = language.lower()
        self.country = country.upper()
        self.client = client if client else httpx.Client()
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
            except:
                logging.debug(f"Failed to parse item: {item}")
            
        return parsed_items
        
    async def _async_resolve_internal_links(self,items:list[NewsItem])->list[NewsItem]:
        async with httpx.AsyncClient() as client:
            for item in items:
                try:
                    if item.is_google_internal_link:
                        response = await client.get(item.link)
                        if response.status_code == MOVED_STATUS_CODE:
                            item.link = response.headers['Location']
                except:
                    logging.debug(f"Failed to resolve internal link: {item.link}")
        return items
    
    def _resolve_internal_links(self,items:list[NewsItem])->list[NewsItem]:
        for item in items:
            try:
                if item.is_google_internal_link:
                    response = self.client.get(item.link)
                    if response.status_code == MOVED_STATUS_CODE:
                        item.link = response.headers['Location']
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
        
        
        