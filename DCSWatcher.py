import json
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from DCSCommon import create_influx_client, process_dcs_data, logger, config

class DCSFileHandler(FileSystemEventHandler):
    def __init__(self, client_factory):
        self.client_factory = client_factory
        self.client = None
        self._ensure_client()
        
    def _ensure_client(self):
        """Ensure we have a working InfluxDB client"""
        if self.client is None:
            try:
                self.client = self.client_factory()
                # Test the connection
                self.client.ping()
                logger.info("Successfully connected to InfluxDB")
                return True
            except Exception as e:
                logger.error(f"Failed to connect to InfluxDB: {str(e)}")
                self.client = None
                return False
        return True
        
    def on_created(self, event):
        if event.is_directory:
            return
            
        if event.src_path.endswith('.dcs.json'):
            # Ensure we have a working client
            if not self._ensure_client():
                logger.warning(f"Cannot process {event.src_path} - InfluxDB connection failed")
                return
                
            try:
                with open(event.src_path, 'r') as f:
                    data = json.load(f)
                process_dcs_data(self.client, data)
                logger.info(f"Processed {event.src_path}")
            except Exception as e:
                logger.error(f"Error processing {event.src_path}: {str(e)}")
                self.client = None  # Force reconnection on next attempt

if __name__ == "__main__":
    # Check if data directory exists
    if not os.path.exists(config['paths']['data_dir']):
        logger.error(f"Data directory does not exist: {config['paths']['data_dir']}")
        exit(1)
        
    # Set up the file watcher
    event_handler = DCSFileHandler(create_influx_client)
    observer = Observer()
    observer.schedule(event_handler, path=config['paths']['data_dir'], recursive=False)
    observer.start()

    logger.info("Starting DCS file watcher...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping DCS file watcher...")
        observer.stop()
    observer.join()