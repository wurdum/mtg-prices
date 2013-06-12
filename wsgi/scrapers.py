# coding=utf-8
import eventlet
import csv
from eventlet.green import urllib2
from bs4 import BeautifulSoup
import models
import ext


def get_redactions():
    """Parses redactions using magiccards, spellshop, buymagic

    :return: list of models.Redaction
    """
    redas = MagiccardsScraper.get_redas()
    redas = SpellShopScraper.update_redas(redas)
    redas = BuyMagicScraper.update_redas(redas)

    return redas


def uni(value):
    """
    Makes input string unicode, clears it and lowers
    """
    if isinstance(value, str):
        value = unicode(value, 'utf-8')
    return value.strip().lower()


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

        try:
            page = urllib2.urlopen(page_url).read()
            soup = BeautifulSoup(page)

            if not MagiccardsScraper._is_card_page(soup):
                hint = MagiccardsScraper._try_get_hint(soup)
                if hint is not None:
                    name = hint.text
                    page_url = ext.url_join(ext.get_domain(page_url), hint['href'])
                    page = urllib2.urlopen(page_url).read()
                    soup = BeautifulSoup(page)

            soup = MagiccardsScraper._select_reda(name, redaction, soup)

            info = MagiccardsScraper._get_card_info(soup)
            price = MagiccardsScraper._get_prices(soup)

            card_info = models.CardInfo(**info)
            card_prices = models.CardPrices(**price)
        except:
            raise Exception('card %s %s was not found' % (name, redaction))
        else:
            return models.Card(name.strip().lower(), redaction.strip().lower(), info=card_info, prices=card_prices)

    @staticmethod
    def _select_reda(name, reda, soup):
        """Finds cards redaction page and returns it

        :param name: card name
        :param reda: redaction name
        :param soup: current card page soup
        :return: soup page with correct redaction
        """
        content_table = soup.find_all('table')[3]
        redas_td = content_table.find_all('td')[2]

        if uni(redas_td.find_all('b')[3].text.split('(')[0]) == reda:
            return soup

        for reda_tag in redas_td.find_all('a'):
            if reda_tag.text.strip().lower() == reda:
                url = ext.url_join(ext.get_domain(MagiccardsScraper.MAGICCARDS_BASE_URL), reda_tag['href'])
                page = urllib2.urlopen(url).read()
                return BeautifulSoup(page)

        raise Exception('card "%s" with redaction "%s" was not found' % (name, reda))

    @staticmethod
    def _is_card_page(soup):
        """Parses soup page and find out is page has card info

        :param soup: soup page from www.magiccards.info
        :return: boolean value
        """
        return len(soup.find_all('table')) > 2

    @staticmethod
    def _try_get_hint(soup):
        """Parses soup page and tries find out card hint

        :param soup: soup page from www.magiccards.info
        :return: tag 'a' with hint
        """
        hints_list = soup.find_all('li')
        return hints_list[0].contents[0] if hints_list else None

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
        sid = uni(ext.get_query_string_params(request_url)['sid'])

        tcg_scrapper = TCGPlayerScraper(sid)

        return tcg_scrapper.get_brief_info()

    @staticmethod
    def get_redas():
        """Parses www.magiccards.info for available redactions

        :return: list of models.Redaction
        """
        url = ext.url_join(MagiccardsScraper.MAGICCARDS_BASE_URL, MagiccardsScraper.MAGICCARDS_REDACTIONS_URL)
        page = urllib2.urlopen(url).read()
        soup = BeautifulSoup(page)

        en_reda_table = soup.find_all('table')[1]
        redas = []
        redas_synonyms = MagiccardsScraper._get_redas_synonyms()
        for reda_a in en_reda_table.find_all('a'):
            name = uni(reda_a.text)
            url = ext.url_join(MagiccardsScraper.MAGICCARDS_BASE_URL, reda_a['href'])
            reda_synonyms = redas_synonyms.get(name, [])

            redas.append(models.Redaction(name, url, reda_synonyms))

        return redas

    @staticmethod
    def _get_redas_synonyms():
        synonyms = {}
        with open('redactions', 'r') as rfile:
            reader = csv.DictReader(rfile, delimiter=';')
            for line in reader:
                key = uni(line['magiccards'])
                spellshop = uni(line['spellshop'])
                buymagic = uni(line['buymagic'])

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
        tcg_response = urllib2.urlopen(self.brief_url).read()
        html_response = tcg_response.replace('\'+\'', '').replace('\\\'', '"')[16:][:-3]

        tcg_soup = BeautifulSoup(html_response)

        prices = {'sid': uni(self.sid),
                  'url': ext.get_domain_with_path(tcg_soup.find('td', class_='TCGPHiLoLink').contents[0]['href']),
                  'low': uni(tcg_soup.find('td', class_='TCGPHiLoLow').contents[1].contents[0]),
                  'mid': uni(tcg_soup.find('td', class_='TCGPHiLoMid').contents[1].contents[0]),
                  'high': uni(tcg_soup.find('td', class_='TCGPHiLoHigh').contents[1].contents[0])}

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
        page = urllib2.urlopen(SpellShopScraper.BASE_URL).read()
        soup = BeautifulSoup(page)

        menu_list = soup.find_all('td', class_='menu_body')[1]
        redactions_container = menu_list.find('table').contents[1].contents[0]
        redaction_divs = redactions_container.find_all('div')[3:37]

        for rdiv in redaction_divs:
            reda_tag = rdiv.find('a')
            name = uni(reda_tag.text)
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
        page = urllib2.urlopen(url).read()
        soup = BeautifulSoup(page)

        cards_table = soup.find('td', class_='td_center')
        cards = []
        if cards_table is not None:
            cards_divs = cards_table.find_all('div')
            pool = eventlet.GreenPool(len(cards_divs))
            for card in pool.imap(SpellShopScraper._parse_card_shop_info, map(lambda cd: (cd, reda), cards_divs)):
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

        name = uni(card_tds[1].find('a').text)
        url = ext.url_join(ext.get_domain(SpellShopScraper.BASE_URL), card_tds[1].find('a')['href'])
        price = ext.uah_to_dollar(card_tds[4].text)
        number = len(card_tds[5].find_all('option'))

        card = MagiccardsScraper.get_card(name, reda.name)
        card.shops.append(models.Shop(SpellShopScraper.SHOP_NAME, url, price, number))

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
        page = urllib2.urlopen(BuyMagicScraper.BASE_URL).read()
        page = page \
            .replace('"bordercolor="#000000" bgcolor="#FFFFFF"', '') \
            .replace('<link rel="stylesheet" href="/jquery.fancybox-1.3.0.css" type="text/css" media="screen">', '') \
            .replace('"title=', '" title=')
        soup = BeautifulSoup(page, from_encoding='utf-8')

        root_div = soup.find_all('div', class_='c1')[1]
        for reda_ul in root_div.find_all('ul')[1:]:
            for reda_tag in reda_ul.find_all('a'):
                name = uni(reda_tag.text)
                url = reda_tag['href']

                reda = ext.get_first(redas, lambda r: name in r.names)
                if reda is None:
                    raise Exception('unknown redaction is found: ' + name)

                reda.shops[BuyMagicScraper.SHOP_NAME] = url

        return redas