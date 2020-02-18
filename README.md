# Google Headlines

Collect the headlines from Google News.

## Install

```bash
virtualenv venv
source venv/bin/activate

pip install -r requirements.txt
```

## Run

Get headlines

```bash
python -m google_headlines
```

Search URLs of articles

'''bash
python -m google_headlines.google_search ../narrative-comparison/data/search_requests.json ../narrative-comparison/data/search_responses.json
```

## Know issues

- GDPR consent Washington Post
- Chrome not closing all the times (Firefox gets stuck sometimes)
