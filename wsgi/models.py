class Card(object):
    """
    Card model with info and prices
    """

    def __init__(self, name, redaction, type, info, prices, shops=None):
        self.name = name
        self.redaction = redaction
        self.type = type
        self.prices = prices
        self.info = info
        self.shops = shops if shops else []

    def __hash__(self):
        return hash((self.name, self.redaction))

    def __eq__(self, other):
        return (self.name, self.redaction) == (other.name, other.redaction)

    def __repr__(self):
        return '%s x %s' % (self.name, self.redaction)


class CardInfo(object):
    """
    Card info from www.magiccards.com
    """

    def __init__(self, url, img_url):
        self.url = url
        self.img_url = img_url

    def __repr__(self):
        return self.url


class CardPrices(object):
    """
    Card info from TCGPlayer
    """

    def __init__(self, sid, url, low, mid, high):
        self.sid = sid
        self.url = url
        self.low = low
        self.mid = mid
        self.high = high

    def __repr__(self):
        return "%s: l[%s] m[%s] h[%s]" % (self.url, self.low, self.mid, self.high)


class Shop(object):
    """
    Represents shop offer for some card
    """

    def __init__(self, name, url, price, number, type='common'):
        self.name = name
        self.url = url
        self.price = price
        self.number = number
        self.type = type

    def __hash__(self):
        return hash((self.name, self.url))

    def __eq__(self, other):
        return (self.name, self.url) == (other.name, other.url)

    def __repr__(self):
        return '%s %s %s' % (self.name, self.type, self.url)


class Redaction(object):
    """
    Represents card redaction
    """

    def __init__(self, name, url, synonyms, shops=None):
        self.name = name
        self.url = url
        self.synonyms = synonyms
        self.shops = {} if not shops else shops

    @property
    def names(self):
        names = list(self.synonyms)
        names.insert(0, self.name)
        return names

    def __repr__(self):
        return '%s [%s]' % (self.name, ', '.join(self.synonyms))