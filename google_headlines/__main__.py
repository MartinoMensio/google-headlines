import typer
import datetime
from threading import Timer
import schedule
import time
import traceback

from . import scraper, utils

app = typer.Typer()

@app.command()
def clean():
    utils.clean()

@app.command()
def scrape(force: bool = False, date: str = utils.get_today()):
    print('scraping NOW')
    max_trials = 10
    done = False
    while max_trials > 0 and not done:
        try:
            scraper.main(force, date)
            done = True
        except Exception as e:
            max_trials -= 1
            traceback.print_exc()
            print(f'******* TERMINATION EXCEPTION: retrials available {max_trials} ***')

    raise ValueError('FINISHED: let\'s free some memory!')

@app.command()
def periodic(time_str: str = '16:00'):
    today = utils.get_today()
    
    hour, minute = time_str.split(':')
    hour, minute = int(hour), int(minute)
    time_planned = datetime.time(hour, minute, 0)

    datetime_now = datetime.datetime.utcnow()
    time_now = datetime.time(datetime_now.hour, datetime_now.minute, datetime_now.second)

    print(f'periodic called today={today} at {time_now} with planned time {time_planned}')

    # initial checks
    if time_now < time_planned:
        print(f'for today not yet executed, executing at {time_planned}')
    else:
        print(f'should have already executed it, let\'s check')
        today_status = scraper.check_date(today)
        if today_status == 'ok':
            print('today was already done')
        elif today_status == 'not_yet':
            print('wasn\'t done today, let\'s run it now')
            scrape()
        elif today_status == 'error':
            print('for today it was started but not completed, running again')
            scrape()
        else:
            raise ValueError()

    print(f'Scheduling next run at {time_str}')
    schedule.every().day.at(time_str).do(scrape)

    while True:
        schedule.run_pending()
        time.sleep(60) # wait one minute
        # print('waiting')

def do_test(n):
    if n % 2:
        raise ValueError(f'oooh {n}')
    print('done', n)

@app.command()
def test():
    print('starting tests')
    n = 0
    print(f'now: {x}')
    schedule.every(5).seconds.do(lambda: do_test(n))

    while True:
        schedule.run_pending()
        n += 1
        print('waiting')
        time.sleep(1)



if __name__ == "__main__":
    app()