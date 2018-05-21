from gevent.pywsgi import WSGIServer
from lib.server import app
import logging, os

logging.basicConfig(level = logging.DEBUG)

http_server = WSGIServer(('', 5000), app)
http_server.serve_forever()
