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

    for c in cards:
        db.cards.insert(todict(c))


def get_shop_cards(shop, skip=0, limit=50):
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    for card_dict in db.cards.find().sort('$natural', -1).skip(skip).limit(limit):
        pass


def update_redas(redas):
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    db.redas.remove()
    for reda in redas:
        db.redas.insert(todict(reda))


def get_redas():
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    redas = []
    for reda_dict in db.redas.find():
        reda = toreda(reda_dict)

        redas.append(reda)

    return redas


def tocard(dict_card):
    """
    Converts dict to card
    """
    info = models.CardInfo(**dict_card['info']) if 'info' in dict_card and dict_card['info'] else None
    prices = models.CardPrices(**dict_card['prices']) if 'prices' in dict_card and dict_card['prices'] else None
    return models.Card(dict_card['name'], dict_card['number'], info=info, prices=prices)


def toreda(dict_reda):
    return models.Redaction(dict_reda['name'], dict_reda['url'], synonyms=dict_reda['synonyms'])


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