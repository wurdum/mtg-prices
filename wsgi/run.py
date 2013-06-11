from flask import Flask, render_template, request

app = Flask(__name__)

#Create our index or root / route
@app.route("/")
@app.route("/index")
def index():
    return "This is the application mynote & I'm alive"

if __name__ == "__main__":
    app.run(debug = "True")