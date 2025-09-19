from flask import Flask
from vercel_wsgi import handle_request

app = Flask(__name__)

@app.route('/')
def home():
    return 'Hello World!'

# Adicione suas outras rotas aqui

def handler(request, context):
    return handle_request(app, request)
