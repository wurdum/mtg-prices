import time
from flask import Flask, render_template, request, redirect, url_for
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


@app.route('/spellshop')
def spellshop():
    redas = filter(lambda r: 'spellshop' in r.shops, db.get_redas())
    cards = []
    start_time = time.time()
    for reda in redas[2:3]:
        cards += scrapers.SpellShopScraper.get_cards(reda)
    print time.time() - start_time, "seconds"
    return render_template('spellshop.html', cards=cards)


if __name__ == "__main__":
    app.run(debug="True")