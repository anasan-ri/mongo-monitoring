# main.py
from flask import Flask, Response
from prometheus_client import make_wsgi_app
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from collector import MongoCollector
import os, logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mongodb-metrics-app")

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://mongo-service:27017")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "10"))
PORT = int(os.environ.get("PORT", "8000"))

collector = MongoCollector(mongo_uri=MONGO_URI, poll_interval=POLL_INTERVAL)
collector.start()

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ MongoDB Metrics Exporter running. Visit /metrics for Prometheus metrics.\n", 200

@app.route("/healthz")
def health():
    return "ok\n", 200

# Expose prometheus metrics at /metrics
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

if __name__ == "__main__":
    logger.info("Starting flask app - connecting to %s", MONGO_URI)
    app.run(host="0.0.0.0", port=PORT)
