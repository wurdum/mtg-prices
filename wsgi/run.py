from flask import Flask, render_template, redirect, url_for
import scrapers
import db
import filters

app = Flask(__name__)
filters.register(app)


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


@app.route('/spellshop/all', defaults={'reda': 'all'}, methods=['GET'])
@app.route('/spellshop/<reda>', methods=['GET'])
def spellshop(reda):
    shops = [scrapers.SpellShopScraper.SHOP_NAME]
    redas = filter(lambda r: all([shop in r.shops for shop in shops]), db.get_redas())
    cards = db.get_cards(shops=shops, redas=None if reda == 'all' else [reda])

    return render_template('spellshop.html', active_reda=reda, redas=redas, cards=cards)


@app.route('/spellshop/update/all', defaults={'reda': 'all'}, methods=['GET'])
@app.route('/spellshop/update/<reda>', methods=['GET'])
def spellshop_update(reda):
    redas = filter(lambda r: 'spellshop' in r.shops,
                   db.get_redas() if reda == 'all' else db.get_redas(name=reda))

    cards = []
    for r in redas:
        cards += scrapers.SpellShopScraper.get_cards(r)

    db.save_cards(cards, shops=[scrapers.SpellShopScraper.SHOP_NAME])

    return redirect(url_for('spellshop', reda=reda))


if __name__ == "__main__":
    app.run(debug="True")