# coding=utf-8
import eventlet
import csv
from eventlet.green import urllib2
from bs4 import BeautifulSoup
import models
import ext


def resolve_cards_async(content):
    """Parses card info using MagiccardScrapper in thread for request mode

    :param content: list of (card_name, card_number) tuples
    :return: list of models.Card objects
    """
    pool = eventlet.GreenPool(len(content))
    return [card for card in pool.imap(MagiccardsScraper.resolve_card, content)]


class MagiccardsScraper(object):
    """
    Parses cards info using www.magiccards.info resource
    """

    MAGICCARDS_BASE_URL = 'http://magiccards.info/'
    MAGICCARDS_REDACTIONS_URL = 'sitemap.html'
    MAGICCARDS_QUERY_TMPL = 'query?q=!%s&v=card&s=cname'

    def __init__(self, name=None, redaction=None):
        self.name = name
        self.redaction = redaction

    @staticmethod
    def resolve_card(name, redaction):
        """Parses card info

        :param name: card name
        :param redaction: card redaction
        :return: models.Card object
        """
        scrapper = MagiccardsScraper(name, redaction)
        return scrapper.get_card()

    def get_card(self):
        """Parses card info, if no info returns card object without info and prices

        :return: models.Card object
        """
        page_url = self.MAGICCARDS_BASE_URL + self.MAGICCARDS_QUERY_TMPL % urllib2.quote(self.name)

        try:
            page = urllib2.urlopen(page_url).read()
            soup = BeautifulSoup(page, from_encoding='utf-8')

            if not self._is_card_page(soup):
                hint = self._try_get_hint(soup)
                if hint is not None:
                    page_url = ext.url_join(ext.get_domain(page_url), hint['href'])
                    self.name = hint.text
                    page = urllib2.urlopen(page_url).read()
                    soup = BeautifulSoup(page, from_encoding='utf-8')

            info = self._get_card_info(soup)
            price = self._get_prices(soup)

            card_info = models.CardInfo(**info)
            card_prices = models.CardPrices(**price)
        except:
            return models.Card(self.name, self.redaction)
        else:
            return models.Card(self.name, self.redaction, info=card_info, prices=card_prices)

    def _is_card_page(self, soup):
        """Parses soup page and find out is page has card info

        :param soup: soup page from www.magiccards.info
        :return: boolean value
        """
        return len(soup.find_all('table')) > 2

    def _try_get_hint(self, soup):
        """Parses soup page and tries find out card hint

        :param soup: soup page from www.magiccards.info
        :return: tag 'a' with hint
        """
        hints_list = soup.find_all('li')
        return hints_list[0].contents[0] if hints_list else None

    def _get_card_info(self, soup):
        """Parses soup page and returns dict with card info

        :param soup: soup page from www.magiccards.info
        :return: dictionary with card info
        """
        content_table = soup.find_all('table')[3]
        return {'url': self._get_url(content_table),
                'img_url': self._get_img_url(content_table),
                'description': self._get_description(content_table)}

    def _get_url(self, table):
        """Parses info table

        :param table: info table at www.magiccards.info
        :return: url of the page with card
        """
        return ext.url_join(MagiccardsScraper.MAGICCARDS_BASE_URL, table.find_all('a')[0]['href'])

    def _get_img_url(self, table):
        """Parses info table

        :param table: info table at www.magiccards.info
        :return: url of the card image
        """
        return table.find_all('img')[0]['src']

    def _get_description(self, table):
        """Parses info table

        :param table: info table at www.magiccards.info
        :return: list of paragraphs of card's description
        """
        dirty_descr = str(table.find_all('p', class_='ctext')[0].contents[0])
        clean_descr = dirty_descr.replace('<b>', '').replace('</b>', '').replace('</br>', '').split('<br><br>')
        return clean_descr

    def _get_prices(self, magic_soup):
        """Parses prices by TCGPlayer card sid

        :param magic_soup: soup page from www.magiccards.info
        :return: dictionary with prices from TCGPlayer in format {sid, low, mid, high}
        """
        content_table = magic_soup.find_all('table')[3]
        request_url = content_table.find_all('script')[0]['src']
        sid = ext.get_query_string_params(request_url)['sid']

        tcg_scrapper = TCGPlayerScraper(sid)

        return tcg_scrapper.get_brief_info()

    def get_en_redas(self):
        url = ext.url_join(self.MAGICCARDS_BASE_URL, self.MAGICCARDS_REDACTIONS_URL)
        page = urllib2.urlopen(url).read()
        soup = BeautifulSoup(page)

        en_reda_table = soup.find_all('table')[1]
        redas = []
        redas_synonyms = self._get_redas_synonyms()
        for reda_a in en_reda_table.find_all('a'):
            name = reda_a.text.strip().lower()
            url = ext.url_join(self.MAGICCARDS_BASE_URL, reda_a['href'])
            reda_synonyms = redas_synonyms.get(name, [])

            redas.append(models.Redaction(name, url, reda_synonyms))

        return redas

    def _get_redas_synonyms(self):
        synonyms = {}
        with open('redactions', 'r') as rfile:
            reader = csv.DictReader(rfile, delimiter=';')
            for line in reader:
                key = line['magiccards'].strip().lower()
                spellshop = line['spellshop'].strip().lower()
                buymagic = line['buymagic'].strip().lower()

                synonyms[key] = [spellshop, buymagic]

        return synonyms


class TCGPlayerScraper(object):
    """
    Parses card prices from TCGPlayer using its sid
    """

    BRIEF_BASE_URL = 'http://partner.tcgplayer.com/x3/mchl.ashx?pk=MAGCINFO&sid='
    FULL_BASE_URL = 'http://store.tcgplayer.com/productcatalog/product/getpricetable' \
                    '?captureFeaturedSellerData=True&pageSize=50&productId='
    FULL_URL_COOKIE = ('Cookie', 'SearchCriteria=WantGoldStar=False&MinRating=0&MinSales='
                                 '&magic_MinQuantity=1&GameName=Magic')

    def __init__(self, sid):
        self.sid = sid

    @property
    def brief_url(self):
        """
        Url to summary card prices
        """
        return self.BRIEF_BASE_URL + self.sid

    @property
    def full_url(self):
        """
        Url to table with seller <-> count <-> price data
        """
        return self.FULL_BASE_URL + self.sid

    def get_brief_info(self):
        """Parses summary price info for card

        :return: dictionary {sid, tcg card url, low, mid, high}
        """
        tcg_response = urllib2.urlopen(self.brief_url).read()
        html_response = tcg_response.replace('\'+\'', '').replace('\\\'', '"')[16:][:-3]

        tcg_soup = BeautifulSoup(html_response)

        prices = {'sid': self.sid,
                  'url': ext.get_domain_with_path(tcg_soup.find('td', class_='TCGPHiLoLink').contents[0]['href']),
                  'low': str(tcg_soup.find('td', class_='TCGPHiLoLow').contents[1].contents[0]),
                  'mid': str(tcg_soup.find('td', class_='TCGPHiLoMid').contents[1].contents[0]),
                  'high': str(tcg_soup.find('td', class_='TCGPHiLoHigh').contents[1].contents[0])}

        return prices


class SpellShopScraper(object):

    BASE_URL = 'http://spellshop.com.ua/index.php?categoryID=90'

    def get_redactions(self):
        page = urllib2.urlopen(self.BASE_URL).read()
        soup = BeautifulSoup(page)

        menu_list = soup.find_all('td', class_='menu_body')[1]
        redactions_container = menu_list.find('table').contents[1].contents[0]
        redaction_divs = redactions_container.find_all('div')[3:37]

        redactions = []
        for rdiv in redaction_divs:
            redaction = rdiv.find('a').text.strip().lower()
            redactions.append(redaction)

        return redactions
