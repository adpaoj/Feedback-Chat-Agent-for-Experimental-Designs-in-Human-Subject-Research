from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello from our Chat Tool!"

if __name__ == '__main__':
    app.run(debug=True)