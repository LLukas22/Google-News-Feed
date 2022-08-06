import src
from src.google_news_feed import GoogleNewsFeed,NewsItem
from datetime import datetime,date
from lxml import etree
from lxml.etree import _Element

def test_build_ceid_should_build_ceid():
    assert 'hl=en-US&gl=US&ceid=US:en' == GoogleNewsFeed()._build_ceid('US', 'en')
    
def test_build_query_should_escape_query():
    assert 'ELON%20MUSK' == GoogleNewsFeed()._build_query("ELON MUSK")
    
def test_parse_item_shoudl_parse_item():
    item = etree.Element("p")
    title = etree.SubElement(item, 'title')
    title.text = "Title"
    link = etree.SubElement(item, 'link')
    link.tail='http://www.foobar.com'
    pubDate = etree.SubElement(item, 'pubdate')
    pubDate.text = "2020-01-01"
    description = etree.SubElement(item, 'description')
    description.text = '<a href="http://www.foobar.com">Foobar</a>'
    source = etree.SubElement(item, 'source')
    source.text = 'source'
    
    news_item = GoogleNewsFeed()._parse_item(item)
    assert isinstance(news_item, NewsItem)
    assert news_item.description == 'Foobar'
    assert news_item.title == 'Title'
    assert news_item.link == 'http://www.foobar.com'
    assert news_item.pubDate == datetime(2020,1,1)
    assert news_item.source == 'source'
    
def test_query_should_return_news_items():
    news_items = GoogleNewsFeed(resolve_internal_links=False).query("Python")
    assert len(news_items) > 0
    assert isinstance(news_items[0], NewsItem)  
    
def test_query_works_with_start_date():
    news_items = GoogleNewsFeed(resolve_internal_links=False).query("Python",after=date(2020,1,1))
    assert len(news_items) > 0
    assert isinstance(news_items[0], NewsItem)  
    
    
def test_query_works_with_end_date():
    news_items = GoogleNewsFeed(resolve_internal_links=False).query("Python",before=date(2020,1,1))
    assert len(news_items) > 0
    assert isinstance(news_items[0], NewsItem) 
    
def test_query_works_with_start_and_end_date():
    news_items = GoogleNewsFeed(resolve_internal_links=False).query("Python",after=date(2020,1,1),before=date(2021,1,1))
    assert len(news_items) > 0
    assert isinstance(news_items[0], NewsItem) 
    
def test_query_works_with_interval():
    news_items = GoogleNewsFeed(resolve_internal_links=False).query("Python",when="3m")
    assert len(news_items) > 0
    assert isinstance(news_items[0], NewsItem)
    
def test_query_topic_should_return_news_items():
    news_items = GoogleNewsFeed(resolve_internal_links=False).query_topic("world")
    assert len(news_items) > 0
    assert isinstance(news_items[0], NewsItem)
    
def test_top_headlines_should_return_news_items():
    news_items = GoogleNewsFeed(resolve_internal_links=False).top_headlines()
    assert len(news_items) > 0
    assert isinstance(news_items[0], NewsItem)
    
def test_internal_link_are_resolved():
    news_items = GoogleNewsFeed().top_headlines()
    assert len(news_items) > 0
    for news_item in news_items:
        assert not news_item.is_google_internal_link