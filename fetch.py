#! /usr/bin/env python3

import collections
import httpcache
import logging
import lxml.html
import os
import requests
import sys
import time

import utils

# This code emulates a state machine.
# Every function takes a state and returns a new function to execute on the
# modified state. The machine is then executed by the Machine class.
class State:
    def __init__(self, uri, sleep, element):
        self.uri = uri
        self.sleep = sleep
        self.element = element

    session = None
    response = None
    previous = None
    hashes = collections.deque(maxlen=1024*1024)

# The current function returns the next function to executed.
# It's quite nice that if you don't return anything the machine will stop.
class Machine:
    def __init__(self, events):
        while len(events) > 0:
            (f, *args) = events.pop(0)
            events.extend(f(*args))


def create_session(state):
    s = requests.Session()
    s.mount('http://', httpcache.CachingHTTPAdapter())
    s.mount('https://', httpcache.CachingHTTPAdapter())
    state.session = s
    logging.info("Created HTTP session with cache")
    return [(fetch_index, state)]


# get a page using the HTTP cache, if the page is not modified return the one
# that is in the internal cache
def fetch_index(state):
    logging.info("Fetching page %s", state.uri)
    state.response = utils.get_page_by_uri(state.session, state.uri)
    return [(check_source, state)]


# check if the content of the page is changed or not
def check_source(state):
    if not state.previous or state.response.text != state.previous.text:
        # current_hash = hash(state.response.text)
        # if current_hash in state.hashes:
        #     logging.warning("Page changed but content is not new")

        # state.hashes.append(current_hash)
        state.previous = state.response
        logging.info("Page changed")
        return [(get_content, state)]

    return [(sleep, state)]


# save the page and some interesting links on disk
def get_content(state):
    path = 'data/' + time.strftime('%Y%m%d-%H:%M:%S', time.gmtime(time.time()))
    dom = lxml.html.fromstring(state.response.text)
    childs = dom.xpath(utils.xpath_for_class(state.element) + '//h3/a/@href')

    if len(childs) > 0:
        os.makedirs(path)
        logging.info("Saving page content in %s/", path)
        utils.save_page_in(path, "main.html", state.response.text)

        absolute_uris = [utils.absolute_uri(state.uri, u) for u in childs]
        return [(process_pages, state, path, absolute_uris)]

    return [(sleep, state)]


# save and eventually send the form for a set of interesting pages
def process_pages(state, path, uris):
    # If the link is broken or there is a 500 from the server?
    # get_page_by_uri should be quite robust because retries
    contents = [utils.get_page_by_uri(state.session, u).text for u in uris]
    names = ["child-" + str(i) + ".html" for i in range(len(contents))]

    # Save all the stuff in the data directory
    for name, uri, content in zip(names, uris, contents):
        logging.info("Saving page %s in %s/%s", uri, path, name)
        utils.save_page_in(path, name, content)

    return [(maybe_fill_forms, state, uris, contents)]


def maybe_fill_forms(state, uris, contents):
    for uri, content in zip(uris, contents):
        dom = lxml.html.fromstring(content)
        if not dom.forms:
            logging.error("Page %s has no forms", uri)
            continue

        form = dom.forms[0]
        current_hash = hash(frozenset(form.fields))
        if current_hash not in state.hashes:
            logging.info("Filling and sending form for page %s", uri)
            state.hashes.append(current_hash)
            response = utils.fill_form_and_send(form)
            if response:
                logging.info("Received %s", str(response))

    return [(sleep, state)]


def sleep(state):
    time.sleep(state.sleep)
    return [(fetch_index, state)]


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

    uri = sys.argv[1]
    sleep = int(sys.argv[2])
    element = sys.argv[3]
    Machine([(create_session, State(uri, sleep, element))])


if __name__ == '__main__':
    main()
