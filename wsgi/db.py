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

    for card in cards:
        card_selector = {'name': card.name, 'redaction': card.redaction}
        dbcard = db.cards.find_one(card_selector)
        if dbcard is not None:
            for k, v in tocard(dbcard).shops.items():
                if k not in card.shops:
                    card.shops[k] = v

            db.cards.update(card_selector, {'$set': {'shops': todict(card.shops)}})
        else:
            db.cards.insert(todict(card))


def get_card(name, reda):
    """Searches card by redaction and name

    :param name: card name
    :param reda: card redaction
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    dbcard = db.cards.find_one({'name': name, 'redaction': reda})
    return tocard(dbcard) if dbcard is not None else None


def get_cards(shop, redas=None, skip=None, limit=None):
    """Returns all cards from db as list of models.Card

    :param shop: shop name
    :param redas: list of redaction for which cards will be searched, list of strings
    :param skip: number of cards that will be skipped
    :param limit: number of cards in result list
    :return: list of models.Card
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    selector = {'shops.' + shop: {'$exists': 1}}
    if redas:
        selector['redaction'] = {'$in': redas}

    sort = [['shops.' + shop + '.overpay', pymongo.DESCENDING]]

    return [tocard(card_dict) for card_dict in db.cards.find(selector).sort(sort).skip(skip).limit(limit)]


def get_cards_count(shop=None, redas=None):
    """Returns number of cards in db

    :param shop: shop name
    :param redas: list of redaction for which cards will be searched, list of strings
    :return: int
    """
    connection = pymongo.MongoClient(MONGO_URL)
    db = connection[DB]

    selector = {}
    if shop:
        selector['shops.' + shop] = {'$exists': 1}
    if redas:
        selector['redaction'] = {'$in': redas}

    return db.cards.find(selector).count()


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
    shops = dict([(k, models.Shop(**v)) for k, v in dict_card['shops'].items()])
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