from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/diensten")
def diensten():
    return render_template("diensten.html")


@app.route("/portfolio")
def portfolio():
    return render_template("portfolio.html")


@app.route("/over-ons")
def over_ons():
    return render_template("over_ons.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True)
