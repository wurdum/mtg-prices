from flask import Flask, render_template, redirect, url_for
import models
import scrapers
import db
import filters

app = Flask(__name__)
filters.register(app)

all_shops = [scrapers.SpellShopScraper, scrapers.BuyMagicScraper]
all_shops_route = '(%s)' % '|'.join(ash.SHOP_NAME for ash in all_shops)
cards_per_page = 40


@app.route('/')
def index():
    return render_template('base.html')


@app.route('/redactions')
def redactions():
    return render_template('redactions.html', redas=sorted(db.get_redas(), key=lambda r: r.name))


@app.route('/redactions/update')
def redactions_update():
    redas = scrapers.get_redactions()

    db.save_redas(redas)

    return redirect(url_for('redactions'))


@app.route('/<regex("(' + all_shops_route + ')"):shop>', defaults={'reda': 'all', 'page': 1}, methods=['GET'])
@app.route('/<regex("(' + all_shops_route + ')"):shop>/<reda>', defaults={'page': 1}, methods=['GET'])
@app.route('/<regex("(' + all_shops_route + ')"):shop>/<reda>/<int:page>', methods=['GET'])
def shop(shop, reda, page):
    if shop not in [sh.SHOP_NAME for sh in all_shops]:
        shop = all_shops[0].SHOP_NAME

    shops = [shop]
    redas = filter(lambda r: all([shop in r.shops for shop in shops]), db.get_redas())
    cards = db.get_cards(shops=shops, redas=None if reda == 'all' else [reda],
                         skip=(page - 1) * cards_per_page, limit=cards_per_page)
    count = db.get_cards_count(shops=shops, redas=None if reda == 'all' else [reda])

    return render_template('shop.html', shop=shop, active_reda=reda, redas=redas, cards=cards,
                           pagination=models.Pagination(page, cards_per_page, count))


@app.route('/<regex("(' + all_shops_route + ')"):shop>/update', defaults={'reda': 'all'}, methods=['GET'])
@app.route('/<regex("(' + all_shops_route + ')"):shop>/update/<reda>', methods=['GET'])
def shop_update(shop, reda):
    if shop not in [sh.SHOP_NAME for sh in all_shops]:
        shop = all_shops[0].SHOP_NAME

    redas = filter(lambda r: shop in r.shops,
                   db.get_redas() if reda == 'all' else db.get_redas(name=reda))

    for r in redas:
        cards = [sh for sh in all_shops if sh.SHOP_NAME == shop][0].get_cards(r)
        db.save_cards(cards)
        print r.name, len(cards)

    return redirect(url_for('shop', shop=shop, reda=reda))


if __name__ == "__main__":
    app.run(debug="True")