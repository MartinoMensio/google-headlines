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
docker start mm35626_google_headlines


# copy locally
rsync -a kmi-web03:/data/user-data/mm35626/google-headlines/data/ ./data

# start bash inside container
sudo docker exec -it mm35626_google_headlines bash
# collect specific day
python3 -m google_headlines scrape --date 2020-08-25
```

## Know issues

- GDPR consent Washington Post
- Some websites deny access from EU
- no collection on 04/07/2020
- no collection between 10/07/2020 and 13/07/2020
- Between 29/07/2020 and 08/08/2020 only articles from "Full coverage"
