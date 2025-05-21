from server.config import get_enabled_operators, DOMAIN_CONFIGS
from server.url_queue import url_queue
import logging
import threading
import time
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class URLWorker:
    def __init__(self):
        self.running = False
        self.thread = None
        self.operators = get_enabled_operators()

    def process_url(self, url_data):
        try:
            # Get domain from URL
            domain = urlparse(url_data['url']).netloc
            
            # Get domain configuration
            if domain not in DOMAIN_CONFIGS:
                logger.warning(f"No configuration found for domain: {domain}")
                return url_data
                
            config = DOMAIN_CONFIGS[domain]
            process_chain = config.get('process_chain', [])
            
            # Process URL with operators in the specified chain order
            for operator_name in process_chain:
                # Find the operator class by name
                operator_class = next((op for op in self.operators if op().name == operator_name), None)
                if operator_class:
                    operator = operator_class()
                    logger.info(f"Processing URL with operator: {operator.name}")
                    url_data = operator.process(url_data['url'], url_data)
                else:
                    logger.warning(f"Operator not found: {operator_name}")
            
            return url_data
        except Exception as e:
            logger.error(f"Error processing URL: {str(e)}")
            return url_data

    def worker_loop(self):
        while self.running:
            try:
                # Get URL from queue
                url_data = url_queue.get()
                if url_data:
                    # Process URL with enabled operators
                    processed_data = self.process_url(url_data)
                    # Handle processed data as needed
                    logger.info(f"Processed URL: {processed_data['url']}")
            except Exception as e:
                logger.error(f"Error in worker loop: {str(e)}")
            time.sleep(1)  # Prevent busy waiting

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.worker_loop)
            self.thread.daemon = True
            self.thread.start()
            logger.info("URL worker started")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
            logger.info("URL worker stopped")

url_worker = URLWorker() 