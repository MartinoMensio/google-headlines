import time
import json
import os
import tqdm
from typing import List
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.action_chains import ActionChains
import chromedriver_binary  # Adds chromedriver binary to path
import geckodriver_autoinstaller # geckodriver for firefox, looks more reliable in quit() and recreate

geckodriver_autoinstaller.install()



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
    with open('data/full_coverage_by_category.json', 'w') as f:
        json.dump(full_coverage_by_category, f, indent=2)
    return full_coverage_by_category

def get_articles_url_from_coverages(driver, full_coverage_by_category):
    result = {}
    if not full_coverage_by_category:
        with open('data/full_coverage_by_category.json') as f:
            full_coverage_by_category = json.load(f)
    for category, coverages in full_coverage_by_category.items():
        print('getting coverages in category', category)
        for c in coverages:
            result[c] = get_articles_url_from_coverage(driver, c)
    return result

def get_articles_url_from_coverage(driver, coverage_url):
    print('getting for url', coverage_url)
    coverage_id = coverage_url.split('/')[-1].split('?')[0]
    coverage_file_name = f'data/cov_{coverage_id}.json'
    if os.path.isfile(coverage_file_name):
        with open(coverage_file_name) as f:
            return json.load(f)

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
            group_title_el: WebElement = group.find_element_by_css_selector('div[data-n-ham]')
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
                    try:
                        driver.quit()
                        del driver
                        driver = webdriver.Firefox()
                        driver.get(u)
                    except Exception:
                        raise ValueError(u)
                resolved_url = driver.current_url
                urls_resolved[u] = resolved_url
            resolved.append(urls_resolved[u])
        groups_resolved[k] = resolved

    # print(groups_resolved)
    with open(coverage_file_name, 'w') as f:
        json.dump(groups_resolved, f, indent=2)
    return groups_resolved
            

def main():
    driver = webdriver.Firefox()
    coverages_by_category = None
    # coverages_by_category = collect_coverages_by_category(driver)
    articles_url = get_articles_url_from_coverages(driver, coverages_by_category)

    driver.quit()

if __name__ == '__main__':
    main()
    