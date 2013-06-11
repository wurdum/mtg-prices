class Card(object):
    """
    Card model with info and prices
    """

    def __init__(self, name, redaction, info=None, prices=None):
        self.name = name
        self.redaction = redaction
        self.prices = prices
        self.info = info
        self.shops = []

    @property
    def has_info(self):
        return self.info is not None

    @property
    def has_prices(self):
        return self.prices is not None

    def __hash__(self):
        return hash((self.name, self.redaction))

    def __eq__(self, other):
        return (self.name, self.redaction) == (other.name, other.redaction)

    def __repr__(self):
        return '%s x %d' % (self.name, self.redaction)


class CardInfo(object):
    """
    Card info from www.magiccards.com
    """

    def __init__(self, url, img_url, description):
        self.url = url
        self.img_url = img_url
        self.description = description

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

    def __init__(self, name, price, number, **kwargs):
        self.name = name
        self.price = price
        self.number = number
        self.__dict__.update(kwargs)


class Redaction(object):

    def __init__(self, name, url, synonyms):
        self.name = name
        self.url = url
        self.synonyms = synonyms

    def __repr__(self):
        return '%s [%s]' % (self.name, ', '.join(self.synonyms))