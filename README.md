# Google Headlines

Collect the headlines from Google News.

## Install

```bash
virtualenv venv
source venv/bin/activate

pip install -r requirements.txt
```

## Run

Get headlines for today

```bash
python -m google_headlines
```

Parameters:

```bash
# Force the recollection of the headlines.
# Warning: the older outputs for today will be overwritten
python -m google_headlines --force True

# To resume the collection interrupted previously on another day
python -m google_headlines --date 2020-03-25

# To delete the temporary files
python -m google_headlines --clean True
```

Search URLs of articles

'''bash
python -m google_headlines.google_search ../narrative-comparison/data/search_requests.json ../narrative-comparison/data/search_responses.json
```

## Know issues

- GDPR consent Washington Post
- Chrome not closing all the times (Firefox gets stuck sometimes)
