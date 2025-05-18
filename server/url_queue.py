import queue
import threading
import time
from server.database import get_db
from server.models import URL, Task, TaskStatus
from server.config import MAX_RETRY_COUNT
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class URLQueue:
    def __init__(self):
        self.url_queue = queue.Queue()
        self.is_running = False
        self.thread = None

    def start(self):
        """启动URL队列处理线程"""
        if not self.is_running:
            self.is_running = True
            self.thread = threading.Thread(target=self._process_urls)
            self.thread.daemon = True
            self.thread.start()
            logger.info("URL queue processor started")

    def stop(self):
        """停止URL队列处理线程"""
        self.is_running = False
        if self.thread:
            self.thread.join()
            logger.info("URL queue processor stopped")

    def _process_urls(self):
        """持续从数据库读取URL并放入队列的处理函数"""
        while self.is_running:
            try:
                db = next(get_db())
                # 获取所有未处理的URL
                urls = db.query(URL).all()
                
                for url in urls:
                    # 检查URL是否已经在任务表中且处理成功
                    existing_task = db.query(Task).filter(
                        Task.url == url.url,
                        Task.status == TaskStatus.SUCCESS
                    ).first()
                    
                    if not existing_task:
                        # 检查是否有失败的任务
                        failed_task = db.query(Task).filter(
                            Task.url == url.url,
                            Task.status == TaskStatus.FAILED
                        ).first()
                        
                        if failed_task:
                            # 检查是否可以重试
                            if failed_task.can_retry(MAX_RETRY_COUNT):
                                # 重置任务状态
                                failed_task.status = TaskStatus.PENDING
                                failed_task.increment_retry()
                                db.commit()
                                
                                # 添加到队列
                                self.url_queue.put(url.url)
                                logger.info(f"Re-added failed URL to queue: {url.url} (retry {failed_task.retry_count})")
                            else:
                                logger.warning(f"URL {url.url} exceeded max retry count ({MAX_RETRY_COUNT})")
                            continue
                        
                        # 检查是否有正在处理的任务
                        processing_task = db.query(Task).filter(
                            Task.url == url.url,
                            Task.status.in_([TaskStatus.PENDING, TaskStatus.PROCESSING])
                        ).first()
                        
                        if not processing_task:
                            # 创建新的任务
                            task = Task(url=url.url)
                            db.add(task)
                            db.commit()
                            
                            # 添加到队列
                            self.url_queue.put(url.url)
                            logger.info(f"Added URL to queue: {url.url}")
                
                # 每60秒检查一次新URL
                time.sleep(60)
            except Exception as e:
                logger.error(f"Error processing URLs: {str(e)}")
                time.sleep(5)  # 发生错误时等待5秒后重试
            finally:
                db.close()

    def get_url(self):
        """从队列中获取一个URL"""
        try:
            return self.url_queue.get_nowait()
        except queue.Empty:
            return None

# 创建全局URL队列实例
url_queue = URLQueue() 