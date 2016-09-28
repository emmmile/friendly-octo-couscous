#! /usr/bin/env python3

import os
import retrying

# some utility functions
@retrying.retry(stop_max_attempt_number=4, wait_exponential_multiplier=1000, wait_exponential_max=32000)
def get_page_by_uri(session, uri):
    headers = {
        # otherwise nginx might reply with 403 Forbidden
        'User-Agent': 'Mozilla/5.0',
    }
    return session.get(uri, headers=headers)


def xpath_for_class(name):
    # http://stackoverflow.com/questions/1604471/how-can-i-find-an-element-by-css-class-with-xpath
    return "//*[contains(concat(' ', normalize-space(@class), ' '), ' " + name + "')]"


def save_page_in(path, filename, content):
    full_path = os.path.join(path, filename)
    with open(full_path, 'w') as output:
        output.write(content)
