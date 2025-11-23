# collector.py
import time
import threading
from pymongo import MongoClient
from prometheus_client import Gauge, Counter, Histogram
import logging

log = logging.getLogger("collector")

class MongoCollector:
    def __init__(self, mongo_uri="mongodb://mongo-service:27017", poll_interval=10):
        self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        self.poll_interval = poll_interval

        # Gauges
        self.mongo_up = Gauge("mongodb_up", "MongoDB reachable (1 = up, 0 = down)")
        self.mongo_connections = Gauge("mongodb_connections_current", "Current number of connections")
        self.mongodb_db_collections = Gauge("mongodb_db_collections_count", "Number of collections in DB", ["db"])
        self.mongodb_collection_documents = Gauge("mongodb_collection_documents_count", "Number of documents in collection", ["db","collection"])
        self.mongodb_query_duration_seconds = Histogram("mongodb_query_duration_seconds", "Histogram of simple query durations")

        # Counters
        self.mongo_poll_errors = Counter("mongodb_poll_errors_total", "Total errors polling MongoDB")

        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def stop(self):
        self._stop.set()
        self._thread.join(timeout=2)

    def _simple_query_latency(self):
        try:
            start = time.time()
            # lightweight ping
            self.client.admin.command("ping")
            duration = time.time() - start
            self.mongodb_query_duration_seconds.observe(duration)
            return duration
        except Exception as e:
            log.debug("simple_query_latency failed: %s", e)
            self.mongo_poll_errors.inc()
            raise

    def _collect(self):
        try:
            server_info = self.client.admin.command("serverStatus")
            self.mongo_up.set(1)
            connections = server_info.get("connections", {}).get("current", 0)
            self.mongo_connections.set(connections)
        except Exception as e:
            log.debug("serverStatus failed: %s", e)
            self.mongo_up.set(0)
            self.mongo_poll_errors.inc()
            return

        try:
            self._simple_query_latency()
        except Exception:
            pass

        try:
            dbs = self.client.list_database_names()
            for db_name in dbs:
                try:
                    db = self.client[db_name]
                    collections = db.list_collection_names()
                    self.mongodb_db_collections.labels(db=db_name).set(len(collections))
                    for coll in collections:
                        try:
                            count = db[coll].estimated_document_count()
                            self.mongodb_collection_documents.labels(db=db_name, collection=coll).set(count)
                        except Exception:
                            continue
                except Exception:
                    continue
        except Exception:
            self.mongo_poll_errors.inc()

    def _run(self):
        while not self._stop.is_set():
            try:
                self._collect()
            except Exception:
                pass
            for _ in range(int(self.poll_interval)):
                if self._stop.is_set():
                    break
                time.sleep(1)
