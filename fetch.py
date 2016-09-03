#! /usr/bin/env python3

import hashlib
import httpcache
import logging
import lxml.html
import os
import requests
import retrying
import sys
import time


@retrying.retry(stop_max_attempt_number=8, wait_exponential_multiplier=1000, wait_exponential_max=64000)
def get_page_by_uri(session, uri):
    headers = {
        # otherwise nginx might reply with 403 Forbidden
        'User-Agent': 'Mozilla/5.0',
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
    BASE_URI = sys.argv[1]
    SLEEP = 64

    session = None
    response = None
    previous = None
    hashes = set()


class Machine:
    def __init__(self, state, f):
        while f:
            f = f(state)


def create_session(state):
    s = requests.Session()
    s.mount('http://', httpcache.CachingHTTPAdapter())
    s.mount('https://', httpcache.CachingHTTPAdapter())
    state.session = s
    logging.info("Created HTTP session with cache")
    return fetch_index


# get a page using the HTTP cache, if the page is not modified return the one
# that is in the internal cache
def fetch_index(state):
    logging.info("Fetching page %s", state.BASE_URI)
    state.response = get_page_by_uri(state.session, state.BASE_URI)
    return check_source


# check if the content of the page is changed or not
def check_source(state):
    if not state.previous or state.response.text != state.previous.text:
        current_hash = hashlib.md5(state.response.text.encode('utf-8'))
        if current_hash in state.hashes:
            logging.warning("Page changed but content is not new")

        state.hashes.add(current_hash)
        state.previous = state.response
        logging.info("Page changed")
        return save_content

    return sleep


# save the page and some interesting links on disk
def save_content(state):
    path = 'output/' + time.strftime('%Y%m%d-%H:%M:%S', time.gmtime(time.time()))
    os.makedirs(path)
    logging.info("Saving page content in %s/", path)
    save_page_in(path, "main.html", state.BASE_URI, state.response.text)

    dom = lxml.html.fromstring(state.response.text)
    for link in dom.xpath(xpath_for_class('subpage-content') + '//a/@href'):
        link_response = get_page_by_uri(state.session, link, 0)
        save_page_in(path, "child.html", link, link_response.text)

    return sleep


def sleep(state):
    time.sleep(state.SLEEP)
    return fetch_index


def main():
    formatter = logging.Formatter('%(asctime)s %(levelname)-7s %(message)s')
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    fh = logging.FileHandler("fetch.log")
    ch = logging.StreamHandler(sys.stdout)
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    root.addHandler(fh)
    root.addHandler(ch)

    Machine(State(), create_session)


if __name__ == '__main__':
    main()
