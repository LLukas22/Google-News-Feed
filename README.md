# Google-News-Feed
A simple python library to consume the google news rss feed.

Inspired by [pygooglenews](https://github.com/kotartemiy/pygooglenews) and implemented using [httpx](https://pypi.org/project/httpx/) and [lxml](https://pypi.org/project/lxml/).


## Installation
Via pip: <code>pip install google-news-feed</code>

## How to use
```python
from google_news_feed import GoogleNewsFeed

gnf = GoogleNewsFeed(language='en',country='US')
results = gnf.query("python")
print(results)
```
For more information about the query parameters see [here](https://newscatcherapi.com/blog/google-news-rss-search-parameters-the-missing-documentaiton).

### Get Top Headlines
```python
gnf = GoogleNewsFeed(language='en',country='US')
results = gnf.top_headlines()
```

### Query a specific topic
```python
gnf = GoogleNewsFeed(language='en',country='US')
results = gnf.query_topic("business")
```
For more topics see [here](https://newscatcherapi.com/blog/google-news-rss-search-parameters-the-missing-documentaiton).
### Accessing the results
The results are a list of NewsItems.
```python
result = gnf.query("python")[0]
print(result.title)
print(result.link)
print(result.pubDate)
print(result.description)
print(result.source)
```

## Handling internal links
Some links are internal to google news. To access the actual link to the news site the internal link has to be accessed and the redirect url is returned. To simplify this process the `resolve_internal_links` property can be set to True.
```python
gnf = GoogleNewsFeed(language='en',country='US',resolve_internal_links=True)
print(gnf.top_headlines()[0].link)
```
The resolution is handled asynchronously by default, but can be forced to be done synchronously via the `run_async` parameter.
