from flask import Flask, render_template, request, redirect, url_for
import scrapers
import db

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('base.html')


@app.route('/ss/0', defaults={'start': 0}, methods=['GET'])
@app.route('/ss/<skip>', methods=['GET'])
def spellshop(skip):
    cards = db.get_shop_cards('spellshop', skip=skip, limit=50)
    return render_template('spellshop.html', cards=cards)


@app.route('/ss/update')
def spellshop_update():
    ss_scraper = scrapers.SpellShopScraper()
    redactions = ss_scraper.get_redactions()
    return redirect(url_for('spellshop'))


@app.route('/redactions')
def redactions():
    return render_template('redactions.html', redas=sorted(db.get_redas(), key=lambda r: r.name))


@app.route('/redactions/update')
def redactions_update():
    redas = scrapers.MagiccardsScraper().get_en_redas()
    db.update_redas(redas)

    return redirect(url_for('redactions'))

if __name__ == "__main__":
    app.run(debug = "True")