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


Docker
```bash
docker build . -t mm35626/google_headlines
#  -v `pwd`/google_headlines:/app/google_headlines
docker run -dit --restart always --name mm35626_google_headlines --shm-size="2G" -v `pwd`/data:/app/data mm35626/google_headlines
docker start google-headlines


scp -r kmi-web03:/data/user-data/mm35626/google-headlines/data ./data-imported
```

## Know issues

- GDPR consent Washington Post
- Chrome not closing all the times (Firefox gets stuck sometimes)
