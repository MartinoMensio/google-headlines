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
    print('scraping NOW')
    max_trials = 10
    while max_trials:
        try:
            scraper.main(force, date)
        except Exception as e:
            max_trials -= 1
            print(f'******* TERMINATION EXCEPTION: retrials available {max_trials} ***')


@app.command()
def periodic(time_str: str = '20:00'):
    x=datetime.today()
    print(f'now: {x}, next run at {time_str}')
    schedule.every().day.at(time_str).do(scrape)

    while True:
        schedule.run_pending()
        time.sleep(60) # wait one minute
        # print('waiting')




if __name__ == "__main__":
    app()