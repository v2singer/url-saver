from sqlalchemy import Column, Integer, String, JSON, Text, DateTime, ARRAY, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlunparse

Base = declarative_base()

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