# RSS Fedder - Financial News RSS Reader with Sentiment Analysis

A Flask-based web application that aggregates financial news from multiple Indian and global RSS feed sources, performs sentiment analysis on article headlines using VADER, and provides auto-generated article summaries. Built for users who want a quick overview of market sentiment across major financial news outlets.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [RSS Feed Sources](#rss-feed-sources)
- [Installation](#installation)
- [Usage](#usage)
- [Application Routes](#application-routes)
- [How It Works](#how-it-works)
- [Future Improvements](#future-improvements)
- [License](#license)

---

## Features

- **Multi-Source RSS Aggregation** - Fetches news from 6 major financial news providers in real-time
- **Sentiment Analysis** - Classifies each article as Positive, Negative, or Neutral using VADER sentiment analysis
- **Article Summarization** - Automatically generates concise summaries by extracting key sentences from full article text
- **Sentiment Dashboard** - Visual breakdown of positive, negative, and neutral sentiment percentages across all feeds
- **Per-Provider Feed View** - Browse articles filtered by individual news sources with provider-specific sentiment stats
- **Full-Text Search** - Search articles by keyword across all stored articles
- **Pagination** - Paginated article listings (10 per page) for easy browsing
- **Session-Based Authentication** - Login-protected routes with session management
- **Auto Cleanup** - Automatically purges articles older than 24 hours to keep the database lean
- **Responsive Design** - Mobile-friendly UI with gradient-based modern styling

---

## Tech Stack

| Component            | Technology                        |
|----------------------|-----------------------------------|
| Backend Framework    | Flask 3.1.2                       |
| RSS Parsing          | feedparser 6.0.12                 |
| Sentiment Analysis   | vaderSentiment 3.3.2              |
| Web Scraping         | requests 2.31.0 + BeautifulSoup4  |
| Database             | SQLite3 (file-based, `feeds.db`)  |
| Templating           | Jinja2                            |
| NLP Libraries        | NLTK 3.8.1, sumy 0.8.0           |
| Frontend             | HTML5, CSS3 (inline styles)       |

---

## Project Structure

```
RSSfedder/
├── app.py                  # Main Flask application (routes, DB, sentiment, scraping)
├── requirements.txt        # Python dependencies
├── feeds.db                # SQLite database (auto-created on first run)
├── templates/
│   ├── base.html           # Base template with header, navbar, footer, and shared styles
│   ├── login.html          # Login page (standalone, does not extend base)
│   ├── index.html          # Home page - paginated list of all articles
│   ├── dashboard.html      # Dashboard - stats, sentiment overview, feed source cards
│   ├── feed.html           # Per-provider feed view with sentiment stats
│   └── search.html         # Search results page
└── .venv/                  # Python virtual environment
```

---

## RSS Feed Sources

| Provider           | Feed Type        |
|--------------------|------------------|
| Yahoo Finance      | Global markets   |
| CNBCTV 18          | Indian business  |
| Money Control      | Indian markets   |
| Economic Times     | Indian markets   |
| Business Standard  | Indian business  |
| Livemint           | Finance & news   |

---

## Installation

### Prerequisites

- Python 3.8+
- pip

### Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd RSSfedder
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv .venv

   # Windows
   .venv\Scripts\activate

   # Linux/macOS
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download NLTK data (required by sumy/VADER)**
   ```bash
   python -c "import nltk; nltk.download('punkt'); nltk.download('vader_lexicon')"
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Open in browser**
   ```
   http://127.0.0.1:5000
   ```

---

## Usage

### Login

Use the demo credentials displayed on the login page:
- **Username:** `ayush`
- **Password:** `123`

Upon login, the application fetches fresh articles from all 6 RSS feeds, scrapes full article content, runs sentiment analysis, generates summaries, and stores everything in the SQLite database.

### Navigation

- **News Feed** (`/`) - Browse all articles across providers with sentiment badges and summaries
- **Dashboard** (`/dashboard`) - Overview with sentiment analytics, quick search, feed source cards, and latest articles from each provider
- **Provider Feed** (`/feed/<provider>`) - View articles from a specific provider with dedicated sentiment stats
- **Search** (`/search?q=<query>`) - Search articles by title keyword

---

## Application Routes

| Route                | Method     | Description                              |
|----------------------|------------|------------------------------------------|
| `/login`             | GET, POST  | Authentication page                      |
| `/`                  | GET        | Home - all articles (paginated)          |
| `/dashboard`         | GET        | Dashboard with stats and sentiment       |
| `/feed/<provider>`   | GET        | Articles from a specific feed provider   |
| `/search?q=<query>`  | GET        | Search articles by keyword               |
| `/logout`            | GET        | End session and redirect to login        |

---

## How It Works

### 1. Article Fetching
On login, `fetch_and_store_articles()` iterates over all configured RSS feeds, parses them with `feedparser`, and for each entry:
- Extracts title, link, and publish date from the RSS feed
- Scrapes the full article page using `requests` + `BeautifulSoup` (with a 5-second timeout)
- Strips scripts, styles, navs, and footers to extract clean body text (truncated to 3000 chars)

### 2. Sentiment Analysis
Each article title is analyzed using **VADER** (Valence Aware Dictionary and sEntiment Reasoner):
- Compound score >= 0.05 &rarr; **Positive**
- Compound score <= -0.05 &rarr; **Negative**
- Otherwise &rarr; **Neutral**
- The raw compound score is normalized to a 0-1 scale and stored

### 3. Summarization
Full article text is summarized using a heuristic sentence-extraction method:
- Splits text into sentences using regex (`(?<=[.!?])\s+`)
- Returns the first 3 sentences as the summary
- Skips articles with fewer than 50 words

### 4. Storage & Cleanup
- Articles are stored in SQLite with `INSERT OR IGNORE` to prevent duplicates (unique constraint on `link`)
- Articles older than 24 hours are automatically deleted on each fetch cycle

---

## Future Improvements

### Short-Term Enhancements
- **Proper User Authentication** - Replace hardcoded credentials with hashed passwords (e.g., `bcrypt`) and a `users` table in the database. Add registration, password reset, and multi-user support.
- **Environment Variables for Configuration** - Move `secret_key`, database path, and credentials out of source code into a `.env` file using `python-dotenv`.
- **Background Feed Fetching** - Move article fetching to a background task (using Celery, APScheduler, or a cron job) instead of blocking the login request. Fetching 6 feeds with full page scraping can take 30+ seconds.
- **Better Summarization** - Replace the simple first-3-sentences heuristic with an extractive summarizer like `sumy` (already in requirements) using LSA or TextRank algorithms, or use an LLM API for abstractive summaries.
- **Content-Based Sentiment** - Analyze full article content for sentiment instead of only the headline, for more accurate classification.
- **CSRF Protection** - Add Flask-WTF for CSRF token protection on all forms.
- **Error Handling & Flash Messages** - Use Flask's `flash()` for user-facing error/success messages instead of returning plain text.

### Medium-Term Features
- **User-Configurable Feeds** - Allow users to add/remove RSS feed sources through the UI instead of hardcoding them.
- **Bookmarks & Read Later** - Let users save articles for later reading.
- **Category/Topic Tagging** - Auto-categorize articles (e.g., stocks, crypto, commodities, policy) using keyword matching or NLP topic modeling.
- **Sentiment Trend Charts** - Add time-series charts (using Chart.js or Plotly) showing sentiment trends over hours/days.
- **Email/Push Notifications** - Alert users when sentiment shifts dramatically (e.g., sudden spike in negative news).
- **REST API** - Expose article and sentiment data via a JSON API for integration with other tools or dashboards.
- **Caching Layer** - Cache RSS feed results and scraped articles with Redis or Flask-Caching to reduce redundant network requests.
- **Pagination Optimization** - Use SQL `LIMIT`/`OFFSET` queries instead of fetching all rows and slicing in Python.

### Long-Term Vision
- **Multi-Language Support** - Add RSS feeds in Hindi, Tamil, and other languages with multilingual sentiment models.
- **Machine Learning Sentiment Model** - Train a custom FinBERT or domain-specific sentiment classifier on financial news for higher accuracy than VADER.
- **Stock Correlation Dashboard** - Correlate sentiment trends with actual stock price movements using market data APIs (e.g., Yahoo Finance API, NSE data).
- **User Analytics** - Track reading habits and recommend articles based on user interest patterns.
- **Deployment & Scaling** - Containerize with Docker, deploy on a cloud platform (AWS/GCP/Heroku), and switch from SQLite to PostgreSQL for production use.
- **PWA Support** - Convert to a Progressive Web App for offline reading and mobile home screen access.
- **RSS Feed Health Monitoring** - Detect and alert when an RSS feed goes down or changes its URL structure.

---

## License

This project is for educational and personal use.
