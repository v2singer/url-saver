import threading
import time
import logging
from server.url_queue import url_queue
from server.rule import url_processor

logger = logging.getLogger(__name__)

class URLWorker:
    def __init__(self):
        self.is_running = False
        self.thread = None
        self.processing_interval = 1  # 处理间隔（秒）

    def start(self):
        """启动工作线程"""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._process_queue)
            self.thread.daemon = True
            self.thread.start()
            logger.info("URL worker started")

    def stop(self):
        """停止工作线程"""
        self.is_running = False
        if self.thread:
            self.thread.join()
            logger.info("URL worker stopped")

    def _process_queue(self):
        """处理队列中的URL"""
        while self.is_running:
            try:
                # 从队列中获取URL
                url = url_queue.get_url()
                
                if url:
                    logger.info(f"Processing URL: {url}")
                    # 使用URL处理器处理URL
                    success = url_processor.process_url(url)
                    
                    if success:
                        logger.info(f"Successfully processed URL: {url}")
                    else:
                        logger.error(f"Failed to process URL: {url}")
                else:
                    # 如果队列为空，等待一段时间
                    time.sleep(self.processing_interval)
                    
            except Exception as e:
                logger.error(f"Error in worker thread: {str(e)}")
                time.sleep(self.processing_interval)

# 创建全局工作线程实例
url_worker = URLWorker() 