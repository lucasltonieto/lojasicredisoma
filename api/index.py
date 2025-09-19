from app import app
from vercel_wsgi import handle

# Ponto de entrada executado pelo Vercel
def handler(request, context):
    return handle(app, request, context)
