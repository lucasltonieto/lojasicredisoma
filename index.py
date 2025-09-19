from app import app
from vercel_wsgi import handle

# A função que o Vercel executa
def handler(request, context):
    return handle(app, request, context)


