#! /usr/bin/env python3

import requests
import retrying
import logging
import os
import time
import lxml.html


@retrying.retry(stop_max_attempt_number=8, wait_exponential_multiplier=1000, wait_exponential_max=64000)
def get_page_by_uri(session, uri, if_modified_since):
    headers = {
        # otherwise nginx might reply with 403 Forbidden
        'User-Agent': 'Mozilla/5.0',
        'If-Modified-Since': time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(if_modified_since))
    }
    return session.get(uri, headers=headers)


def xpath_for_class(name):
    # http://stackoverflow.com/questions/1604471/how-can-i-find-an-element-by-css-class-with-xpath
    return "//*[contains(concat(' ', normalize-space(@class), ' '), ' " + name + "')]"


def save_page_in(path, filename, uri, content):
    full_path = os.path.join(path, filename)
    with open(full_path, 'w') as output:
        output.write(content)


# This code emulates a state machine.
# Every function takes a state and returns a new function to execute on the
# modified state. The machine is then executed by the Machine class.
class State:
    BASE_URI = 'http://wahlinfastigheter.se/lediga-objekt/lagenhet/'
    SLEEP = 64

    session = None
    response = None
    last_fetch = 0


class Machine:
    def __init__(self, state, f):
        while f:
            f = f(state)


def create_session(state):
    s = requests.Session()
    state.session = s
    logging.info("Created HTTP session")
    return fetch_page


# get a page using the HTTP cache, if the page is not modified return the one
# that is in the internal cache
def fetch_page(state):
    logging.info("Fetching page %s", state.BASE_URI)
    state.response = get_page_by_uri(state.session, state.BASE_URI, state.last_fetch)
    state.last_fetch = time.time()
    return check_source


def check_source(state):
    if state.response.status_code == 200:
        logging.info("Page changed")
        return save_content

    return sleep


def save_content(state):
    path = time.strftime('%Y%m%d-%H:%M:%S', time.gmtime(time.time()))
    os.makedirs(path)
    logging.info("Saving page content in ./%s/", path)
    save_page_in(path, "index.html", state.BASE_URI, state.response.text)

    dom = lxml.html.fromstring(state.response.text)
    for link in dom.xpath(xpath_for_class('subpage-content') + '//a/@href'):
        link_response = get_page_by_uri(state.session, link, 0)
        save_page_in(path, "link.html", link, link_response.text)

    return sleep


def sleep(state):
    time.sleep(state.SLEEP)
    return fetch_page


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-7s %(message)s')
    Machine(State(), create_session)
