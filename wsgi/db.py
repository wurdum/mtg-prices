import os
import pymongo
import models

MONGO_URL = os.environ.get('OPENSHIFT_MONGODB_DB_URL', 'localhost')
DB = os.environ.get('OPENSHIFT_APP_NAME', 'prices')


def save_cards(cards):
    """
    Saves cards list to db with token as key
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    db.cards.remove()
    for c in cards:
        db.cards.insert(todict(c))


def get_cards(shops=None, redas=None):
    """
    Returns all cards from db as list of models.Card
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    selector = {}
    if shops:
        selector['shops.name'] = {'$in': shops}
    if redas:
        selector['redaction'] = {'$in': redas}

    return [tocard(card_dict) for card_dict in db.cards.find(selector)]


def save_redas(redas):
    """
    Removes old and saves new redactions list to db
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    db.redas.remove()
    for reda in redas:
        db.redas.insert(todict(reda))


def get_redas(name=None):
    """
    Loads redactions list from db

    :param name: redaction name that will be searched
    :return: list of models.Redaction
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    selector = {} if name is None else {'name': name}
    return [toreda(reda_dict) for reda_dict in db.redas.find(selector)]


def tocard(dict_card):
    """
    Converts dict to models.Card
    """
    info = models.CardInfo(**dict_card['info']) if 'info' in dict_card and dict_card['info'] else None
    prices = models.CardPrices(**dict_card['prices']) if 'prices' in dict_card and dict_card['prices'] else None
    shops = [models.Shop(**shop_dict) for shop_dict in dict_card['shops']]
    return models.Card(dict_card['name'], dict_card['redaction'], dict_card['type'],
                       info=info, prices=prices, shops=shops)


def toreda(dict_reda):
    """
    Converts dict to models.Redaction
    """
    return models.Redaction(dict_reda['name'], dict_reda['url'], dict_reda['synonyms'], shops=dict_reda['shops'])


def todict(obj, classkey=None):
    """
    Converts object graph to dict structures
    """
    if isinstance(obj, dict):
        for k in obj.keys():
            obj[k] = todict(obj[k], classkey)
        return obj
    elif hasattr(obj, "__iter__"):
        return [todict(v, classkey) for v in obj]
    elif hasattr(obj, "__dict__"):
        data = dict([(key, todict(value, classkey))
                     for key, value in obj.__dict__.iteritems()
                     if not callable(value) and not key.startswith('_')])
        if classkey is not None and hasattr(obj, "__class__"):
            data[classkey] = obj.__class__.__name__
        return data
    else:
        return obj