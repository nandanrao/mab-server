from gevent.pywsgi import WSGIServer
from lib.server import app
import os

http_server = WSGIServer(('', 5000), app)
http_server.serve_forever()
