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


def get_cards():
    """
    Returns all cards from db as list of models.Card
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    return [tocard(card_dict) for card_dict in db.cards.find()]


def save_redas(redas):
    """
    Removes old and saves new redactions list to db
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    db.redas.remove()
    for reda in redas:
        db.redas.insert(todict(reda))


def get_redas():
    """
    Loads redactions list from db
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    return [toreda(reda_dict) for reda_dict in db.redas.find()]


def tocard(dict_card):
    """
    Converts dict to card
    """
    info = models.CardInfo(**dict_card['info']) if 'info' in dict_card and dict_card['info'] else None
    prices = models.CardPrices(**dict_card['prices']) if 'prices' in dict_card and dict_card['prices'] else None
    shops = [models.Shop(**shop_dict) for shop_dict in dict_card['shops']]
    return models.Card(dict_card['name'], dict_card['redaction'], info=info, prices=prices, shops=shops)


def toreda(dict_reda):
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