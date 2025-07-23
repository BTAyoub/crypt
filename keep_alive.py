from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def keep_alive():
    app.run(host='0.0.0.0', port=8080)
