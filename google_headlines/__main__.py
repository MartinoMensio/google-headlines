import typer
from datetime import datetime, timedelta
from threading import Timer
import schedule
import time

from . import scraper, utils

app = typer.Typer()

@app.command()
def clean():
    utils.clean()

@app.command()
def scrape(force: bool = False, date: str = utils.get_today()):
    print('scraping')
    max_trials = 10
    while max_trials:
        try:
            scraper.main(force, date)
        except Exception as e:
            raise e
            max_trials -= 1


@app.command()
def periodic():
    x=datetime.today()
    print(f'now: {x}')
    schedule.every().day.at("16:26").do(scrape)

    while True:
        schedule.run_pending()
        time.sleep(60) # wait one minute
        # print('waiting')




if __name__ == "__main__":
    app()