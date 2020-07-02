import os
import re
import time
import tqdm
# import psutil
import requests

from typing import List
from functools import wraps
import urllib.parse as urlparse
from collections import defaultdict
from multiprocessing.pool import ThreadPool

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException, InsecureCertificateException
from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException


from . import utils

import chromedriver_binary  # Adds chromedriver binary to path
import geckodriver_autoinstaller # geckodriver for firefox, looks more reliable in quit() and recreate
geckodriver_autoinstaller.install()


#############################################################################
# webdriver utilities
#############################################################################

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

def get_webdriver(headless=True, browser='firefox'):
    if browser == 'chrome':
        options = ChromeOptions()
        options.add_argument('--disable-dev-shm-usage')
        options.headless = headless
        driver = webdriver.Chrome(options=options)
    elif browser == 'firefox':
        options = FirefoxOptions()
        options.headless = headless
        driver = webdriver.Firefox(options=options)
    # driver.minimize_window()
    return driver

def terminate_webdriver(driver):
    ## experiment to see if it works
    try:
        # if driver.service.process:
        #     p = psutil.Process(driver.service.process.pid)
        #     pids = p.children(recursive=True)
        # else:
        #     pids = []
        driver.close()
        driver.quit()
        # for p_one in pids:
        #     print('terminating', p_one.pid)
        #     p_one.terminate()
    except Exception as e:
        print(e)


def select_stories_in_section_from_url(url, driver=None):
    """From a url that matches `/topics/{topic_id}(/sections/{section_id})?` retrieves a list of `/stories{story_id}`.

    `driver` argument is optional. If provided it will be used, otherwise a new driver will be used
    """
    # check if url is matching
    if not url.startswith('https://news.google.com/topics/'):
        raise ValueError(url)
    if not driver:
        driver = get_webdriver(headless=True)
        is_new_driver = True
        driver.get('http://networkcheck.kde.org/')
        time.sleep(1)
        driver.get(url)
    else:
        is_new_driver = False
    result = select_stories_in_section(driver)
    print(len(result))
    if is_new_driver:
        terminate_webdriver(driver)
    return result
    


def select_stories_in_section(driver):
    """From the current page `/topics/{topic_id}(/sections/{section_id})?` retrieves a list of `/stories{story_id}`"""

    # get all the links in the page
    links = [el.get_attribute('href') for el in driver.find_elements_by_tag_name('a')]
    # filter the ones that point to stories. This selection is robust to any language
    links = [el for el in links if (el and el.startswith('https://news.google.com/stories/'))]
    print('all', len(links))
    links = list(dict.fromkeys(links).keys())
    print('unique', len(links))
    
    return links


def get_full_coverage_pages_by_category(driver):
    result = {}

    driver = get_webdriver()

    driver.get("https://news.google.com/topstories?hl=en-GB&gl=GB&ceid=GB:en")
    more_headlines_el = driver.find_element_by_link_text('More Headlines')
    more_headlines_el.click()
    time.sleep(5)
    index_update(driver.current_url)
    sections_el : List[WebElement] = driver.find_elements_by_xpath('//div[@data-scrollbar="true"]/div')
    print('found', len(sections_el), 'sections')

    sections_urls = {}
    for c in sections_el:
        # get the section name
        section_name = c.get_attribute('innerText').strip()
        if not section_name:
            # something is wrong (dummy/clutter sections)
            continue
        # scroll horizontally to the element
        actions = ActionChains(driver)
        actions.move_to_element(c).perform()
        # go on the section
        c.click()
        sections_urls[section_name] = driver.current_url

    terminate_webdriver(driver)

    for section_name, section_url in sections_urls.items():
        # this is awful but to have a clean DOM, use a different instance of driver for every section
        section_stories = select_stories_in_section_from_url(section_url)
        print(f'section {section_name} has {len(section_stories)} stories')
        
        result[section_name] = section_stories
    
    return result



def collect_coverages_by_category(driver):
    full_coverage_by_category = get_full_coverage_pages_by_category(driver)
    date = utils.get_today()
    file_path = f'data/full_coverage_by_category_{date}.json'
    
    utils.save_json(file_path, full_coverage_by_category)
    

    return full_coverage_by_category, file_path

def get_articles_url_from_coverages(full_coverage_by_category, date):
    result = {}
    def single_wrapper(c):
        result_one = get_articles_url_from_coverage_cached(c)
        return c, result_one

    file_path = f'data/full_coverage_by_category_{date}.json'

    pool = ThreadPool(4)
    for category, coverages in full_coverage_by_category.items():
        print('getting coverages in category', category)
        for c, result_one in pool.imap_unordered(single_wrapper, coverages):
            result[c] = result_one
    return result

def get_story_id_from_url(url):
    return url.split('/')[-1].split('?')[0]

def get_articles_url_from_coverage_cached(coverage_url):
    coverage_id = get_story_id_from_url(coverage_url)
    coverage_file_name = f'data/tmp/cov_{coverage_id}.json'
    # look if already there
    if os.path.isfile(coverage_file_name):
        # print('cached found for', coverage_url)
        return utils.read_json(coverage_file_name)
    # call the real function
    result = get_articles_url_from_coverage(coverage_url)
    # save results
    utils.save_json(coverage_file_name, result)

    return result

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
    # with short timeout
    driver.set_page_load_timeout(5)
    single_wrapper = lambda u: (u, resolve_url(u))
    pool = ThreadPool(8)
    for k, google_urls in groups_urls.items():
        print('visiting news for group', k)
        resolved = []
        for u, resolved_url in tqdm.tqdm(pool.imap(single_wrapper, google_urls), total=len(google_urls)):
        # for u in tqdm.tqdm(google_urls):
        #     if u not in urls_resolved:
        #         resolved_url = resolve_url(driver, u)
        #         urls_resolved[u] = resolved_url
            resolved.append(resolved_url)
        groups_resolved[k] = resolved

    return groups_resolved

def resolve_url(u, tentatives=3):
    # response = requests.head(u, allow_redirects=True)
    # # response.raise_for_status()
    # resolved_url = response.url
    if tentatives == 0:
        # india today https://news.google.com/articles/CAIiENW48loW7b7nJFQVflFbLjYqGQgEKhAIACoHCAowot7cCjD8xM4BMN7VhgI?hl=en-GB&gl=GB&ceid=GB%3Aen
        if u == 'https://news.google.com/articles/CAIiENW48loW7b7nJFQVflFbLjYqGQgEKhAIACoHCAowot7cCjD8xM4BMN7VhgI?hl=en-GB&gl=GB&ceid=GB%3Aen':
            return u
        raise ValueError(u)
    result = u
    try:
        res = requests.head(u, allow_redirects=True, timeout=5)
        result = res.url
    except requests.exceptions.Timeout as e:
        # website dead, return the last one
        print(e)
        result = e.request.url
    except requests.exceptions.InvalidSchema as e:
        # something like a ftp link that is not supported by requests
        print(e)
        error_str = str(e)
        found_url = re.sub("No connection adapters were found for '([^']*)'", r'\1', error_str)
        result = found_url
    except requests.exceptions.RequestException as e:
        print(e)
        # other exceptions such as SSLError, ConnectionError, TooManyRedirects
        if e.request and e.request.url:
            result = e.request.url
        else:
            # something is really wrong
            raise e
    # except Exception as e:
    #     # something like http://ow.ly/yuFE8 that points to .
    #     print('error for',url)

    if 'https://news.google.com/articles/' in result:
        print('trying again...')
        return resolve_url(u, tentatives=tentatives-1)
    return result

def resolve_url_old(driver, u):
    """This is tricky, let's resolve a google article url"""
    # print('visiting news', u)
    try:
        driver.get(u)
    except TimeoutException:
        print('timed out at', driver.current_url)
    except InsecureCertificateException:
        print('InsecureCertificateException at ', driver.current_url)
    except WebDriverException as e:
        message = e.msg
        # firefox network error page
        if message.startswith('Reached error page: '):
            error_url = message.replace('Reached Error Page: ', '')
            error_url = error_url.replace('about:neterror', '')
            print(error_url)
            resolved_url = urlparse.parse_qs(error_url)['u'][0]
            # raise ValueError(resolve_url)
        else:
            raise e
    except Exception as e:
        # RemoteDisconnected
        raise e
        # print('######## RETRYING', u, '##########')
        # # time.sleep(10)
        # terminate_webdriver(driver)
        # del driver
        # driver = get_webdriver()
        # try:
        #     driver.get(u)
        # except Exception:
        #     raise ValueError(u)
    try:
        resolved_url = driver.current_url
    except UnexpectedAlertPresentException:
        try:
            driver.switch_to.alert.dismiss()
        except NoAlertPresentException:
            # this is crazy, but happens
            pass
        resolved_url = driver.current_url
    # wait_cnt = 0
    # while 'https://news.google.com/articles/' in resolved_url:
    #     if wait_cnt > 5:
    #         raise ValueError('Waiting too much', driver.current_url)
    #     if wait_cnt == 2 or wait_cnt == 4:
    #         # firefox sometimes gets stuck
    #         driver.get(u)
    #     print('Waiting extra time...')
    #     time.sleep(5)
    #     resolved_url = driver.current_url
    #     wait_cnt += 1

    # avoid selenium.common.exceptions.StaleElementReferenceException
    ActionChains(driver).send_keys(Keys.ESCAPE)
    if 'https://news.google.com/articles/' in resolved_url:
        try:
            # # Firefox is way faster because this happens a lot (it thinks the page is loaded) so we don't need to go to the destination page
            resolved_url = driver.find_element_by_xpath('//a[@rel="nofollow"]').get_attribute('href')
            print('still on Google News, but the url is', resolved_url)
        except StaleElementReferenceException:
            # if it is stale, the driver.current_url now is the new page
            resolved_url = driver.current_url
            print('stale catched at', resolved_url)
        except NoSuchElementException:
            # and also in this case
            resolved_url = driver.current_url
            print('NoSuchElement at', resolved_url)

    # fix for washingtonpost gdpr
    if resolved_url.startswith('https://www.washingtonpost.com/gdpr-consent/'):
        resolved_url = urlparse.parse_qs(urlparse.urlparse(resolved_url).query)['next_url'][0]

    return resolved_url

def create_headline_file(date, file_path, out_path):
    by_category = utils.read_json(file_path)

    result = defaultdict(list)

    for category_name, category_urls in by_category.items():
        for category_url in category_urls:
            url_id = get_story_id_from_url(category_url)
            urls_by_type = utils.read_json(f'data/tmp/cov_{url_id}.json')
            result[category_name].append({'url': category_url, 'articles': urls_by_type})
    
    utils.save_json(out_path, result)
    return result

def index_update(url):
    index_path = 'data/index.json'
    time = utils.get_time()
    if os.path.isfile(index_path):
        index = utils.read_json(index_path)
    else: 
        index = []
    if any(el['url'] == url for el in index):
        print('already in the index')
        return
    index.append({'url': url, 'time': time})
    utils.save_json(index_path, index)


def main(force=False, date=utils.get_today()):
    # initial file
    file_path = f'data/full_coverage_by_category_{date}.json'
    # final file
    headline_file_path = f'data/headlines_{date}.json'

    collect_new_headlines = False
    if not os.path.isdir('data/tmp'):
        os.makedirs('data/tmp')

    if force:
        if date != utils.get_today():
            print('Too late, you can\'t travel in time (for now)!')
            return
        print(f'Recollecting everything today {date}...')
        collect_new_headlines = True
    elif os.path.isfile(headline_file_path):
        # already done
        print(f'Already done for date {date}, use the force parameter to do again')
        return
    else:
        # not yet
        if os.path.isfile(file_path):
            # initial headlines file is there, so continue
            print('Initial headlines file found, resuming...')
        else:
            # nothing yet, collect new
            collect_new_headlines = True

    if collect_new_headlines:
        print('Collecting new headlines...')
        date = utils.get_today()
        # driver = get_webdriver(headless=True)
        driver = None
        coverages_by_category, file_path = collect_coverages_by_category(driver)
        # terminate_webdriver(driver)
    else:
        coverages_by_category = utils.read_json(file_path)
    
    print(f'Collecting headlines urls, date={date}. Results will be at {headline_file_path}')
    articles_url = get_articles_url_from_coverages(coverages_by_category, date)
    # then put all together
    create_headline_file(date, file_path, out_path=headline_file_path)
    print('Done')
    utils.clean()
