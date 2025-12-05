import feedparser
from flask import Flask, render_template,request

app = Flask(__name__)

RSS_FEED_URL = {
    'Yahoo Finance': 'https://finance.yahoo.com/news/rssindex',
    'CNBCTV 18': 'https://www.cnbctv18.com/market/rssfeed.xml',
    'Money Control': 'https://www.moneycontrol.com/rss/MCtopnews.xml',
    'Economic Times': 'https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms',
    'Business Standard': 'https://www.business-standard.com/rss/home_page_top_stories.rss',
    'Livemint': 'https://www.livemint.com/rss/news',
}

@app.route("/", methods=['GET', 'POST'])

def index():
    articles = []
    for source, url in RSS_FEED_URL.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            articles.append({
                'source': source,
                'title': entry.title,
                'link': entry.link,
                'published': entry.published
            })
    articles.sort(key=lambda x: x['published'], reverse=True)

    page=request.args.get('page', 1, type=int)
    per_page=10
    total_articles=len(articles)
    start=(page-1)*per_page
    end=start+per_page
    paginated_articles=articles[start:end]

    return render_template('index.html', articles=paginated_articles, page=page, total_pages=(total_articles + per_page - 1) // per_page)
@app.route('/search')
def search():
    query = request.args.get('q', '')
    articles = []
    for source, url in RSS_FEED_URL.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if query.lower() in entry.title.lower():
                articles.append({
                    'source': source,
                    'title': entry.title,
                    'link': entry.link,
                    'published': entry.published
                })
    return render_template('search.html', articles=articles, query=query) 

if __name__ == "__main__":
    app.run(debug=True)  
    
