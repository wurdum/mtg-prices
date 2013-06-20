# coding=utf-8
import gzip
import csv
import eventlet
import difflib
from StringIO import StringIO
from eventlet.green import urllib2
from bs4 import BeautifulSoup, Tag
import models
import ext
import db


def get_redactions():
    """Parses redactions using magiccards, spellshop, buymagic

    :return: list of models.Redaction
    """
    redas = MagiccardsScraper.get_redas()
    redas = SpellShopScraper.update_redas(redas)
    redas = BuyMagicScraper.update_redas(redas)

    return redas


def openurl(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.110 Safari/537.36',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4',
        'Accept-Encoding': 'gzip,deflate',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Cache-Control': 'max-age=0'
    }

    opener = urllib2.build_opener()
    opener.addheaders = headers.items()
    response = opener.open(ext.iriToUri(url))

    if response.info().get('Content-Encoding') == 'gzip':
        buf = StringIO(response.read())
        response = gzip.GzipFile(fileobj=buf)

    page = response.read()
    return page


class MagiccardsScraper(object):
    """
    Parses cards info using www.magiccards.info resource
    """

    MAGICCARDS_BASE_URL = 'http://magiccards.info/'
    MAGICCARDS_REDACTIONS_URL = 'sitemap.html'
    MAGICCARDS_QUERY_TMPL = 'query?q=!%s&v=card&s=cname'

    @staticmethod
    def get_card(name, redaction):
        """Parses card info, if no info returns card object without info and prices

        :return: models.Card object
        """
        page_url = MagiccardsScraper.MAGICCARDS_BASE_URL + MagiccardsScraper.MAGICCARDS_QUERY_TMPL % urllib2.quote(name)
        page = openurl(page_url)
        soup = BeautifulSoup(page)

        # if card was not found by name, try to use magiccards hints
        if not MagiccardsScraper._is_card_page(soup):
            hint = MagiccardsScraper._try_get_hint(name, soup)
            if hint is None:
                return None

            name = hint.text
            page_url = ext.url_join(ext.get_domain(page_url), hint['href'])
            page = openurl(page_url)
            soup = BeautifulSoup(page)

        # if card is found, but it's not english
        if not MagiccardsScraper._is_en(soup):
            en_link_tag = list(soup.find_all('table')[3].find_all('td')[2].find('img', alt='English').next_elements)[1]
            name = en_link_tag.text
            page_url = ext.url_join(ext.get_domain(page_url), en_link_tag['href'])
            page = openurl(page_url)
            soup = BeautifulSoup(page)

        # if card redaction is wrong, try to get correct
        if not MagiccardsScraper._reda_is(redaction, soup):
            page_url = MagiccardsScraper._get_correct_reda(redaction, soup)
            if page_url is None:
                return None

            page = openurl(page_url)
            soup = BeautifulSoup(page)

        type = MagiccardsScraper._get_card_type(soup)
        info = MagiccardsScraper._get_card_info(soup)
        price = MagiccardsScraper._get_prices(soup)

        card_info = models.CardInfo(**info)
        card_prices = models.CardPrices(**price)

        return models.Card(ext.uni(name), ext.uni(redaction), type, card_info, card_prices)

    @staticmethod
    def _is_en(soup):
        """
        Checks if found card is en
        """
        en_link = list(soup.find_all('table')[3].find_all('td')[2].find('img', alt='English').next_elements)[1]
        return en_link.name == 'b'

    @staticmethod
    def _reda_is(reda, soup):
        """Checks if card redaction is correct

        :param reda: required card redaction
        :param soup: soup of card page
        """
        content_table = soup.find_all('table')[3]
        redas_td = content_table.find_all('td')[2]

        redas_bs = redas_td.find_all('b')
        # for double sided card 4
        reda_index = 3 if len(redas_bs) == 5 else 4
        return ext.uni(redas_bs[reda_index].text.split('(')[0]) == reda

    @staticmethod
    def _get_correct_reda(reda, soup):
        """Searches correct redaction for card and returns it's url

        :param reda: required card redaction
        :param soup: soup of card page
        """
        content_table = soup.find_all('table')[3]
        redas_td = content_table.find_all('td')[2]

        for reda_tag in redas_td.find_all('a'):
            if reda_tag.text.strip().lower() == reda:
                return ext.url_join(ext.get_domain(MagiccardsScraper.MAGICCARDS_BASE_URL), reda_tag['href'])

        return None

    @staticmethod
    def _is_card_page(soup):
        """Parses soup page and find out is page has card info

        :param soup: soup page from www.magiccards.info
        :return: boolean value
        """
        return len(soup.find_all('table')) > 2

    @staticmethod
    def _try_get_hint(name, soup):
        """Parses soup page and tries find out card hint.
        Selects hint that has max affinity with base card name.

        :param name: cards name
        :param soup: soup page from www.magiccards.info
        :return: tag 'a' with hint
        """
        hints_list = []
        for hint_li in soup.find_all('li'):
            hint_tag = hint_li.contents[0]
            resemble_rate = difflib.SequenceMatcher(a=ext.uni(name), b=ext.uni(hint_li.contents[0].text)).ratio()
            hints_list.append({'a_tag': hint_tag, 'rate': resemble_rate})

        return sorted(hints_list, key=lambda h: h['rate'], reverse=True)[0]['a_tag'] if hints_list else None

    @staticmethod
    def _get_card_type(soup):
        """Parses soup page and returns card type (rare, common, etc.)

        :param soup: soup page from www.magiccards.info
        :return: card type as string
        """
        redas_bs = soup.find_all('table')[3].find_all('td')[2].find_all('b')
        # if double sided card
        reda_index = 3 if len(redas_bs) == 5 else 4
        return ext.uni(redas_bs[reda_index].text.split('(')[1][:-1])

    @staticmethod
    def _get_card_info(soup):
        """Parses soup page and returns dict with card info

        :param soup: soup page from www.magiccards.info
        :return: dictionary with card info
        """
        content_table = soup.find_all('table')[3]
        return {'url': ext.url_join(MagiccardsScraper.MAGICCARDS_BASE_URL, content_table.find_all('a')[0]['href']),
                'img_url': content_table.find_all('img')[0]['src']}

    @staticmethod
    def _get_prices(magic_soup):
        """Parses prices by TCGPlayer card sid

        :param magic_soup: soup page from www.magiccards.info
        :return: dictionary with prices from TCGPlayer in format {sid, low, mid, high}
        """
        content_table = magic_soup.find_all('table')[3]
        request_url = content_table.find_all('script')[0]['src']
        sid = ext.uni(ext.get_query_string_params(request_url)['sid'])

        tcg_scrapper = TCGPlayerScraper(sid)
        prices = tcg_scrapper.get_brief_info()

        return prices

    @staticmethod
    def get_redas():
        """Parses www.magiccards.info for available redactions

        :return: list of models.Redaction
        """
        page_url = ext.url_join(MagiccardsScraper.MAGICCARDS_BASE_URL, MagiccardsScraper.MAGICCARDS_REDACTIONS_URL)
        page = openurl(page_url)
        soup = BeautifulSoup(page)

        en_reda_table = soup.find_all('table')[1]
        redas = []
        redas_synonyms = MagiccardsScraper._get_redas_synonyms()
        for reda_a in en_reda_table.find_all('a'):
            name = ext.uni(reda_a.text)
            url = ext.url_join(MagiccardsScraper.MAGICCARDS_BASE_URL, reda_a['href'])
            reda_synonyms = redas_synonyms.get(name, [])

            redas.append(models.Redaction(name, url, reda_synonyms))

        return redas

    @staticmethod
    def _get_redas_synonyms():
        """
        Parses redactions csv file with redaction synonyms
        and returns dict of {redaction:synonyms}
        """
        synonyms = {}
        with open('redactions', 'r') as rfile:
            reader = csv.DictReader(rfile, delimiter=';')
            for line in reader:
                key = ext.uni(line['magiccards'])
                spellshop = ext.uni(line['spellshop'])
                buymagic = ext.uni(line['buymagic'])

                synonyms[key] = [spellshop, buymagic]

        return synonyms


class TCGPlayerScraper(object):
    """
    Parses card prices from TCGPlayer using its sid
    """

    BRIEF_BASE_URL = 'http://partner.tcgplayer.com/x3/mchl.ashx?pk=MAGCINFO&sid='

    def __init__(self, sid):
        self.sid = sid

    @property
    def brief_url(self):
        """
        Url to summary card prices
        """
        return self.BRIEF_BASE_URL + self.sid

    def get_brief_info(self):
        """Parses summary price info for card

        :return: dictionary {sid, tcg card url, low, mid, high}
        """
        tcg_response = openurl(self.brief_url)
        html_response = tcg_response.replace('\'+\'', '').replace('\\\'', '"')[16:][:-3]

        tcg_soup = BeautifulSoup(html_response)

        prices = {'sid': ext.uni(self.sid),
                  'url': ext.get_domain_with_path(tcg_soup.find('td', class_='TCGPHiLoLink').contents[0]['href']),
                  'low': ext.price_to_float(ext.uni(tcg_soup.find('td', class_='TCGPHiLoLow').contents[1].contents[0])),
                  'mid': ext.price_to_float(ext.uni(tcg_soup.find('td', class_='TCGPHiLoMid').contents[1].contents[0])),
                  'high': ext.price_to_float(ext.uni(tcg_soup.find('td', class_='TCGPHiLoHigh').contents[1].contents[0]))}

        return prices


class SpellShopScraper(object):
    """
    Represents parser for www.spellshop.com.ua
    """

    BASE_URL = 'http://spellshop.com.ua/index.php?categoryID=90'
    SHOP_NAME = u'spellshop'

    @staticmethod
    def update_redas(redas):
        """Parses www.spellshop.com.ua and adds shop info to redactions

        :param redas: list of models.Redaction
        :returns: list of updated models.Redaction
        """
        page = openurl(SpellShopScraper.BASE_URL)
        soup = BeautifulSoup(page)

        menu_list = soup.find_all('td', class_='menu_body')[1]
        redactions_container = menu_list.find('table').contents[1].contents[0]
        redaction_divs = redactions_container.find_all('div')[3:37]

        for rdiv in redaction_divs:
            reda_tag = rdiv.find('a')
            name = ext.uni(reda_tag.text)
            url = ext.url_join(ext.get_domain(SpellShopScraper.BASE_URL), reda_tag['href'])

            reda = ext.get_first(redas, lambda r: name in r.names)
            if reda is None:
                raise Exception('unknown redaction is found: ' + name)

            reda.shops[SpellShopScraper.SHOP_NAME] = url

        return redas

    @staticmethod
    def get_cards(reda):
        """Parses www.spellshop.com.ua to find all available card for reda redaction

        :param reda: cards redaction, object of models.Redaction
        :return: list of models.Card
        """
        url = reda.shops[SpellShopScraper.SHOP_NAME] + '&show_all=yes'
        page = openurl(url)
        soup = BeautifulSoup(page)

        cards_table = soup.find('td', class_='td_center')
        cards = []
        if cards_table is not None:
            cards_divs = filter(lambda d: ext.uni(d.text), cards_table.find_all('div'))
            if len(cards_divs) == 0:
                return cards

            pool = eventlet.GreenPool(len(cards_divs) if len(cards_divs) < 100 else 100)
            for card in pool.imap(SpellShopScraper._parse_card_shop_info, map(lambda cd: (cd, reda), cards_divs)):
                if card is not None:
                    cards.append(card)

        return cards

    @staticmethod
    def _parse_card_shop_info(args):
        """Parses card shop info and find this card at www.magiccard.info

        :param args: tuple of (soup tag with card info, models.Redaction)
        :return: models.Card
        """
        card_div, reda = args
        card_tr = card_div.find('tr')
        card_tds = card_tr.find_all('td')

        name = ext.uni(card_tds[1].find('a').text)
        if name.split()[0] in ['mountain', 'swamp', 'island', 'plains', 'forest']:
            return None

        url = ext.url_join(ext.get_domain(SpellShopScraper.BASE_URL), card_tds[1].find('a')['href'])
        price = ext.price_to_float(ext.uah_to_dollar(card_tds[4].text))
        number = len(card_tds[5].find_all('option'))

        card = db.get_card(name, reda.name)
        if card is None:
            card = MagiccardsScraper.get_card(name, reda.name)

        if card is None:
            return None

        card.shops[SpellShopScraper.SHOP_NAME] = \
            models.Shop(SpellShopScraper.SHOP_NAME, url, price, card.prices.avg / price, number)

        return card


class BuyMagicScraper(object):
    """
    Represents parser for www.buymagic.ua
    """

    BASE_URL = 'http://www.buymagic.com.ua/'
    SHOP_NAME = u'buymagic'

    @staticmethod
    def update_redas(redas):
        """Parses www.buymagic.com.ua and adds shop info to redactions

        :param redas: list of models.Redaction
        :returns: list of updated models.Redaction
        """
        page = openurl(BuyMagicScraper.BASE_URL)
        page = page \
            .replace('"bordercolor="#000000" bgcolor="#FFFFFF"', '') \
            .replace('<link rel="stylesheet" href="/jquery.fancybox-1.3.0.css" type="text/css" media="screen">', '') \
            .replace('"title=', '" title=')
        soup = BeautifulSoup(page, from_encoding='utf-8')

        root_div = soup.find_all('div', class_='c1')[1]
        for reda_ul in root_div.find_all('ul')[1:]:
            for reda_tag in reda_ul.find_all('a'):
                name = ext.uni(reda_tag.text)
                url = reda_tag['href']

                reda = ext.get_first(redas, lambda r: name in r.names)
                if reda is None:
                    raise Exception('unknown redaction is found: ' + name)

                reda.shops[BuyMagicScraper.SHOP_NAME] = url

        return redas

    @staticmethod
    def get_cards(reda):
        """Parses www.buymagic.ua to find all available card for reda redaction

        :param reda: cards redaction, object of models.Redaction
        :return: list of models.Card
        """
        page_url = reda.shops[BuyMagicScraper.SHOP_NAME]
        page = openurl(page_url)
        page = page \
            .replace('"bordercolor="#000000" bgcolor="#FFFFFF"', '') \
            .replace('<link rel="stylesheet" href="/jquery.fancybox-1.3.0.css" type="text/css" media="screen">', '') \
            .replace('"title=', '" title=')
        soup = BeautifulSoup(page, from_encoding='utf-8')

        pager_div = soup.find('div', class_='c2').contents[5]
        pages_tags = pager_div.find_all('a')

        pages = [page_url]
        pages += [ext.url_join(ext.get_domain(BuyMagicScraper.BASE_URL), tag['href']) for tag in pages_tags]

        cards = []
        pool = eventlet.GreenPool(len(pages))
        for page_cards in pool.imap(BuyMagicScraper._parse_cards_at_page, map(lambda p: (p, reda), pages)):
            if page_cards is not None:
                cards += page_cards

        return cards

    @staticmethod
    def _parse_cards_at_page(args):
        """Parses cards that found at current page

        :param args: tuple of (page url, models.Redaction)
        :return: list of models.Card or None
        """
        page_url, reda = args
        page = openurl(page_url)
        page = page \
            .replace('"bordercolor="#000000" bgcolor="#FFFFFF"', '') \
            .replace('<link rel="stylesheet" href="/jquery.fancybox-1.3.0.css" type="text/css" media="screen">', '') \
            .replace('"title=', '" title=')
        soup = BeautifulSoup(page, from_encoding='utf-8')

        root_div = soup.find('div', class_='c2')
        card_divs = filter(lambda r: isinstance(r, Tag), list(root_div.find('p').children))[:-1]

        cards = []
        pool = eventlet.GreenPool(len(card_divs))
        args = map(lambda d: (d, reda), card_divs)
        for card in pool.imap(BuyMagicScraper._parse_card_shop_info, args):
            if card is not None:
                cards.append(card)

        return cards

    @staticmethod
    def _parse_card_shop_info(args):
        """Parses card shop info and find this card at www.magiccard.info

        :param args: tuple of (soup tag with card info, models.Redaction)
        :return: models.Card or None
        """
        card_div, reda = args
        inner_div = card_div.find('div')
        if inner_div is not None:
            card_div = inner_div

        header_tag = card_div.find('a')
        url = ext.uni(header_tag['href'])
        name = ext.uni(header_tag.text)

        price_table = card_div.find('table')
        price_row = price_table.find('tr').find_all('td')
        type = 'common'
        price = ext.price_to_float(ext.uah_to_dollar(ext.uni(price_row[1].text)))
        number = len(price_row[2].find_all('option'))

        card = db.get_card(name, reda.name)
        if card is None:
            card = MagiccardsScraper.get_card(name, reda.name)

        if card is None:
            return None

        card.shops[BuyMagicScraper.SHOP_NAME] = \
            models.Shop(BuyMagicScraper.SHOP_NAME, url, price, card.prices.avg / price, number, type=type)

        return card
