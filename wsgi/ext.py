# coding=utf-8
import re
import urlparse


def uni(value):
    """
    Makes input string unicode, clears it and lowers
    """
    if isinstance(value, str):
        value = unicode(value, 'utf-8')
    return value.strip().lower()


def urlEncodeNonAscii(b):
    """
    Replaces non ascii symbols with encoded
    """
    return re.sub('[\x80-\xFF]', lambda c: '%%%02x' % ord(c.group(0)), b)


def iriToUri(iri):
    """
    Encodes url as special ascii
    """
    parts = urlparse.urlparse(iri)
    return urlparse.urlunparse(urlEncodeNonAscii(part.encode('utf-8')) for parti, part in enumerate(parts))


def uah_to_dollar(uah):
    """Converts uah price to dollar representation

    :param uah: price in format 999.99 грн.
    :return: price in format $999.99
    """
    uah_float_price = float(uah.split()[0])
    dollar_float_price = uah_float_price / 8.0
    return '$%0.2f' % dollar_float_price


def get_first(iterable, func, default=None):
    """
    Returns first element that satisfy condition
    """
    for item in iterable:
        if func(item):
            return item

    return default


def get_domain(url):
    """
    Returns hostname with scheme
    """
    decomposed = urlparse.urlparse(url)
    return decomposed.scheme + '://' + decomposed.hostname


def get_domain_with_path(url):
    """
    Returns hostname with scheme and path
    """
    decomposed = urlparse.urlparse(url)
    return decomposed.scheme + '://' + decomposed.hostname + decomposed.path


def get_query_string_params(url):
    """
    Returns dict of query string parameters
    """
    return dict([(k, v[0]) for k, v in urlparse.parse_qs(urlparse.urlparse(url).query).items()])


def url_join(base, url):
    """
    Joins 2 parts of url
    """
    return urlparse.urljoin(base, url)


def price_to_float(string):
    """Converts string price to float repr, if price is 0 returns 0.01

    :param string: price string repr
    :return: price as float
    """
    if isinstance(string, float):
        return string

    return float(string[1:]) if float(string[1:]) > 0 else 0.01