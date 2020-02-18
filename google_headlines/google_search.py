import json
import typer
import tqdm
import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

from . import get_webdriver, with_webdriver, terminate_webdriver



def clean_browser_data(driver, timeout=5):
    driver.get('chrome://settings/clearBrowserData')

    # wait for the button to appear
    time.sleep(5)

    # # select everything
    # checkboxes = driver.find_elements_by_css_selector('#basic-tab cr-checkbox')
    # for cb in checkboxes:
    #     if not cb.get_attribute('checked'):
    #         cb.click()

    # click the button to clear the cache
    # driver.find_element_by_xpath('//*[@id="clearBrowsingDataConfirm"]').click()
    # raise ValueError(3)
    driver.find_element_by_xpath('//settings-ui').send_keys(Keys.ENTER)

def search_google(query: str, domain: str, driver):
    query_full = f'{query} site:{domain}'
    driver.get(f'https://www.google.com/search?q={query_full}')
    # clean_browser_data(driver)
    elements = driver.find_elements_by_xpath('//a')
    links = [el.get_attribute('href') for el in elements]
    links = [el for el in links if el]
    results = [el for el in links if domain in el]
    if 'https://www.google.com/sorry/index' in driver.current_url:
        print(driver.current_url)
        driver.maximize_window()
        # clean_browser_data(driver)
        print('waiting for human intervention: SOLVE CAPTCHA. If it still fails, go to chrome://settings/clearBrowserData and delete everything. Also use devtools to delete LocalStorage and SessionStorage')
        while 'https://www.google.com/sorry/index' in driver.current_url:
            print('waiting human intervention...')
            time.sleep(10)
        # terminate_webdriver(driver)
        # del driver
        # driver = get_webdriver(headless=False)
        return search_google(query, domain, driver)
    print(len(results))
    return results

@with_webdriver
def search_one(query, domain, **kwargs):
    driver = kwargs['driver']
    results = search_google(query, domain, driver)
    return results


def main(file_in_path: str, file_out_path: str):
    """The input file must be a list of `{'query': QUERY, 'domain': DOMAIN}` objects"""
    with open(file_in_path) as f:
        search_requests = json.load(f)

    driver = get_webdriver(headless=False)
    results = []
    for r in tqdm.tqdm(search_requests, desc='Searching on google'):
        query = r['query']
        domain = r['domain']
        links = search_google(query, domain, driver)
        r['links'] = links
        results.append(r)
    with open(file_out_path, 'w') as f:
        json.dump(results, f, indent=2)

def main_query(query: str, domain: str):
    return search_one(query, domain)

if __name__ == "__main__":
    typer.run(main)