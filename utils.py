#! /usr/bin/env python3

import os
import retrying
import urllib
import logging

import info

# some utility functions
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


def save_page_in(path, filename, content):
    full_path = os.path.join(path, filename)
    with open(full_path, 'w') as output:
        output.write(content)


def absolute_uri(base_uri, link):
    if 'http://' not in link:
        return urllib.parse.urljoin(base_uri, link)
    else:
        return link


# @retrying.retry(stop_max_attempt_number=8, wait_exponential_multiplier=1000, wait_exponential_max=64000)
def fill_form_and_send(form):
    try:
        form.fields.update(info.form_data)
        return form.submit()
    except KeyError:
        logging.error("Key not present in form. Maybe format has changed.")
