from server.models import Base, URL
from server.database import engine, SessionLocal
from sqlalchemy.exc import SQLAlchemyError

def init_db():
    try:
        Base.metadata.create_all(bind=engine)
        print("Database initialized successfully")
    except SQLAlchemyError as e:
        print(f"Error initializing database: {e}")
        raise

def create_url(url_string):
    db = SessionLocal()
    try:
        url = URL(url=url_string)
        db.add(url)
        db.commit()
        db.refresh(url)
        return url
    except SQLAlchemyError as e:
        db.rollback()
        print(f"Error creating URL record: {e}")
        raise
    finally:
        db.close()

def get_all_urls():
    db = SessionLocal()
    try:
        return db.query(URL).all()
    finally:
        db.close()

if __name__ == "__main__":
    # Initialize database
    init_db()
    
    # Example URLs
    test_urls = [
        "https://example.com/path?param1=value1&param2=value2",
        "https://test.com/search?q=python&page=1",
        "https://api.example.com/v1/users?filter=active"
    ]
    
    # Create example URLs
    for test_url in test_urls:
        try:
            url = create_url(test_url)
            print(f"\nCreated URL record:")
            print(f"ID: {url.id}")
            print(f"URL: {url.url}")
            print(f"Domain: {url.domain}")
            print(f"Path: {url.path}")
            print(f"Query Parameters: {url.query_params}")
        except Exception as e:
            print(f"Failed to create URL {test_url}: {e}")
    
    # List all URLs
    print("\nAll URLs in database:")
    for url in get_all_urls():
        print(f"- {url.url} (Domain: {url.domain})") 