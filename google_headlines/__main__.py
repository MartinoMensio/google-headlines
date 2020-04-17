import typer

from . import scraper, utils

app = typer.Typer()

@app.command()
def clean():
    utils.clean()

@app.command()
def scrape(force: bool = False, date: str = utils.get_today()):
    scraper.main(force, date)

if __name__ == "__main__":
    app()