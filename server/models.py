from sqlalchemy import Column, Integer, String, JSON, Text, DateTime, ARRAY, UniqueConstraint, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlunparse
import enum

Base = declarative_base()

class TaskStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"

class ProcessingStage(enum.Enum):
    INIT = "init"
    DOWNLOAD = "download"
    AUDIO_EXTRACT = "audio_extract"
    SUBTITLE_EXTRACT = "subtitle_extract"
    VECTORIZE = "vectorize"

class URL(Base):
    __tablename__ = 'urls'
    __table_args__ = (
        UniqueConstraint('url', name='uix_url'),
    )

    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False, index=True)
    domain = Column(String, nullable=False)
    path = Column(String, nullable=False)
    query_params = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True, default=list)
    notes = Column(Text, nullable=True)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    favicon = Column(String, nullable=True)
    thumbnail = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, url, tags=None, notes=None, **kwargs):
        super().__init__(**kwargs)
        self.tags = tags or []
        self.notes = notes
        self._parse_url(url)

    def _parse_url(self, original_url):
        """Parse the URL and set domain, path, and query parameters."""
        parsed = urlparse(original_url)
        
        # Set domain
        self.domain = parsed.netloc
        
        # Set path
        self.path = parsed.path or '/'
        
        # Parse and set query parameters
        self.query_params = parse_qs(parsed.query) if parsed.query else {}
        
        # Store URL without query parameters
        clean_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            '',  # params
            '',  # query
            ''   # fragment
        ))
        self.url = clean_url

class Task(Base):
    __tablename__ = 'tasks'
    __table_args__ = (
        UniqueConstraint('url', name='uix_task_url'),
    )

    id = Column(Integer, primary_key=True)
    url = Column(String, nullable=False, index=True)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    error_message = Column(Text, nullable=True)
    result_data = Column(JSON, nullable=True)  # 存储处理结果，如视频ID、文件路径等
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)  # 失败重试次数
    current_stage = Column(Enum(ProcessingStage), default=ProcessingStage.INIT)  # 当前处理阶段

    def __init__(self, url, **kwargs):
        super().__init__(**kwargs)
        self.url = url
        self.status = TaskStatus.PENDING
        self.result_data = {}
        self.retry_count = 0
        self.current_stage = ProcessingStage.INIT

    def increment_retry(self):
        """增加重试次数"""
        self.retry_count += 1
        return self.retry_count

    def can_retry(self, max_retries):
        """检查是否可以重试"""
        return max_retries == -1 or self.retry_count < max_retries 