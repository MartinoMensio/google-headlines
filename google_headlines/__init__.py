import time
import datetime
import json
import os
import tqdm
import psutil
import typer
from functools import wraps
from multiprocessing.pool import ThreadPool
from typing import List
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
import chromedriver_binary  # Adds chromedriver binary to path
import geckodriver_autoinstaller # geckodriver for firefox, looks more reliable in quit() and recreate

geckodriver_autoinstaller.install()

def with_webdriver(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        driver = get_webdriver()
        kwargs['driver'] = driver
        try:
            return f(*args, **kwargs)
        finally:
            terminate_webdriver(driver)
    return decorated

def get_webdriver(headless=True):
    options = Options()
    if headless:
        options.set_headless()
    # https://w3c.github.io/webdriver/#dfn-dismissed
    # options.set_capability('unhandledPromptBehaviour', 'dismiss')
    # options.set_capability('unexpectedAlertBehaviour', 'ignore')
    # capabilities.CHROME.['unexpectedAlertBehaviour'] = 'accept'
    driver = webdriver.Chrome(options=options)
    # driver.minimize_window()
    return driver

def terminate_webdriver(driver):
    ## experiment to see if it works
    try:
        if driver.service.process:
            p = psutil.Process(driver.service.process.pid)
            pids = p.children(recursive=True)
        else:
            pids = []
        driver.close()
        driver.quit()
        for p_one in pids:
            print('terminating', p_one.pid)
            p_one.terminate()
    except Exception as e:
        print(e)

@with_webdriver
def get_full_coverage_pages_by_category(driver):
    result = {}

    driver.get("https://news.google.com/")
    more_headlines_el = driver.find_element_by_link_text('More Headlines')
    more_headlines_el.click()
    time.sleep(5)
    categories_el : List[WebElement] = driver.find_elements_by_xpath('//div[@data-scrollbar="true"]/div')
    print(categories_el)

    for c in categories_el:
        # get the category name
        category = c.get_attribute('innerText').strip()
        if not category:
            # something is wrong (dummy/clutter categories)
            continue
        # scroll horizontally to the element
        actions = ActionChains(driver)
        actions.move_to_element(c).perform()
        # go on the category
        c.click()
        # wait async loading
        time.sleep(5)
        full_coverages: List[WebElement] = driver.find_elements_by_partial_link_text('View Full coverage')
        # print([el.get_attribute('href') for el in full_coverages])
        print('category', category, len(full_coverages), 'full coverages')
        result[category] = [el.get_attribute('href') for el in full_coverages]
    
    return result

def collect_coverages_by_category(driver):
    full_coverage_by_category = get_full_coverage_pages_by_category(driver)
    with open('data/full_coverage_by_category_latest.json', 'w') as f:
        json.dump(full_coverage_by_category, f, indent=2)
    file_path = f'data/full_coverage_by_category_{datetime.datetime.utcnow().isoformat()}.json'
    with open(file_path, 'w') as f:
        json.dump(full_coverage_by_category, f, indent=2)

    return full_coverage_by_category, file_path

def get_articles_url_from_coverages(full_coverage_by_category=None, file_path='data/full_coverage_by_category_latest.json'):
    result = {}
    def single_wrapper(c):
        result_one = get_articles_url_from_coverage_cached(c)
        return c, result_one

    pool = ThreadPool(4)
    if not full_coverage_by_category:
        with open(file_path) as f:
            full_coverage_by_category = json.load(f)
    for category, coverages in full_coverage_by_category.items():
        print('getting coverages in category', category)
        for c, result_one in pool.imap_unordered(single_wrapper, coverages):
            result[c] = result_one
    return result

def get_articles_url_from_coverage_cached(coverage_url):
    coverage_id = coverage_url.split('/')[-1].split('?')[0]
    coverage_file_name = f'data/cov_{coverage_id}.json'
    # look if already there
    if os.path.isfile(coverage_file_name):
        print('cached found for', coverage_url)
        with open(coverage_file_name) as f:
            return json.load(f)
    # call the real function
    result = get_articles_url_from_coverage(coverage_url)
    # save results
    with open(coverage_file_name, 'w') as f:
        json.dump(result, f, indent=2)

@with_webdriver
def get_articles_url_from_coverage(coverage_url, **kwargs):
    driver = kwargs['driver']
    print('getting for url', coverage_url)


    groups_urls = {}
    driver.get(coverage_url)
    # //main/div[@data-n-ham]/div[@data-n-ham]                        is a group
    # //main/div[@data-n-ham]/div[@data-n-ham]/div[@data-n-ham]       is the title of the group
    # //main/div[@data-n-ham]/div[@data-n-ham]/div/article            are the articles in the group
    # //main/div[@data-n-ham]/article                                 are the articles in all coverage
    groups: List[WebElement] = driver.find_elements_by_xpath('//main/div[@data-n-ham]/div[@data-n-ham]')
    # print(groups)
    for group in groups:
        group_text = group.get_attribute('innerText').strip()
        if group_text == 'All coverage':
            group_title = 'All coverage'
            articles = driver.find_elements_by_xpath('//main/div[@data-n-ham]/article/a')
        else:
            try:
                group_title_el: WebElement = group.find_element_by_css_selector('div[data-n-ham]')
            except NoSuchElementException as e:
                print('EXCEPTION NoSuchElementException for', coverage_url)
                # e.g. https://news.google.com/stories/CAAqOQgKIjNDQklTSURvSmMzUnZjbmt0TXpZd1NoTUtFUWlpeDVDSmo0QU1FZHRwSGxaR0VPQXZLQUFQAQ?hl=en-GB&gl=GB&ceid=GB%3Aen
                # just skip the group
                continue
            group_title = group_title_el.get_attribute('innerText').strip()
            articles = group.find_elements_by_css_selector('div article a')
        links = [el.get_attribute('href') for el in articles]
        # remove duplicates
        links = set(links)
        # remove none
        links = [el for el in links if el]
        groups_urls[group_title] = links
        # print(group_title, links)
    # print(groups_urls)
    groups_resolved = {}
    # resolve just once, even if it appears multiple times in different groups
    urls_resolved = {}
    # now get the real links to the articles
    for k, google_urls in groups_urls.items():
        print('visiting news for group', k)
        resolved = []
        for u in tqdm.tqdm(google_urls):
            if u not in urls_resolved:
                # print('visiting news', u)
                try:
                    driver.get(u)
                except Exception as e:
                    # RemoteDisconnected
                    print('######## RETRYING', u, '##########')
                    time.sleep(10)
                    terminate_webdriver(driver)
                    del driver
                    driver = get_webdriver()
                    try:
                        driver.get(u)
                    except Exception:
                        raise ValueError(u)
                try:
                    resolved_url = driver.current_url
                except UnexpectedAlertPresentException:
                    try:
                        driver.switch_to.alert.dismiss()
                    except NoAlertPresentException:
                        # this is crazy, but happens
                        pass
                    resolved_url = driver.current_url
                wait_cnt = 0
                while 'https://news.google.com/articles/' in  resolved_url:
                    if wait_cnt > 5:
                        raise ValueError('Waiting too much', driver.current_url)
                    print('Waiting extra time...')
                    time.sleep(5)
                    resolved_url = driver.current_url
                    wait_cnt += 1
                urls_resolved[u] = resolved_url
            resolved.append(urls_resolved[u])
        groups_resolved[k] = resolved

    return groups_resolved
            

def main(collect_new_headlines=False):
    coverages_by_category = None
    file_path = None
    if collect_new_headlines:
        driver = get_webdriver()
        coverages_by_category, file_path = collect_coverages_by_category(driver)
        terminate_webdriver(driver)
        articles_url = get_articles_url_from_coverages(full_coverage_by_category=coverages_by_category, file_path=file_path)
    else:
        articles_url = get_articles_url_from_coverages(coverages_by_category)
    # then ???

if __name__ == '__main__':
    typer.run(main)
    