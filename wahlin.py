#! /usr/bin/env python3

# TODO parsing the page, to see if something is available
# TODO if something is available get second page
# TODO post form
# TODO if I already submitted my request, flood the website with gets

import requests
import retrying
import httpcache
import logging
import time

BASEURI = 'http://wahlinfastigheter.se'
NORMAL_SLEEP = 32
SHORT_SLEEP = 8


def create_session():
    s = requests.Session()
    s.mount('http://', httpcache.CachingHTTPAdapter())
    s.mount('https://', httpcache.CachingHTTPAdapter())
    return s

# get a page using the HTTP cache, if the page is not modified return the one
# that is in the internal cache
@retrying.retry(stop_max_attempt_number=8,
                wait_exponential_multiplier=1000,
                wait_exponential_max=64000)
def get_page(session, uri):
    logging.info("Getting page %s", uri)
    headers = {
        # otherwise nginx might reply with 403 Forbidden
        'User-Agent': 'Mozilla/5.0'
    }

    response = session.get(uri, headers=headers)
    return response.text

def main(session):
    while True:
        source = get_page(session, BASEURI)
        time.sleep(NORMAL_SLEEP)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s %(levelname)-7s %(message)s')
    session = create_session()
    main(session)
