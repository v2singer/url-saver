from flask import Flask, request, jsonify
from flask_cors import CORS
from server.database import get_db, engine
from server.models import URL, Base
from server.url_queue import url_queue
from server.worker import url_worker
from sqlalchemy.exc import SQLAlchemyError
import logging
import traceback
import os
import jieba
import jieba.analyse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 建议接口
@app.route('/extension/suggest', methods=['POST'])
def suggest_tags():
    try:
        data = request.get_json()
        if not data or 'title' not in data:
            return jsonify({'error': 'Title is required'}), 400

        title = data['title']
        url = data.get('url', '')

        # 使用jieba提取关键词
        keywords = jieba.analyse.extract_tags(title, topK=5)
        
        # 使用jieba进行分词
        words = list(jieba.cut(title))
        
        # 过滤掉停用词和单字词
        filtered_words = [word for word in words if len(word) > 1]
        
        # 合并结果并去重
        suggestions = list(set(keywords + filtered_words))
        
        return jsonify({
            'suggestions': suggestions
        })
    except Exception as e:
        error_msg = f"Error generating suggestions: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return jsonify({'error': 'Internal server error'}), 500

# API routes for browser extension
@app.route('/extension/urls', methods=['POST'])
def create_url():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL is required'}), 400

    try:
        db = next(get_db())
        url = URL(
            url=data['url'],
            title=data.get('title', ''),
            tags=data.get('tags', []),
            notes=data.get('notes', '')
        )
        db.add(url)
        db.commit()
        db.refresh(url)
        
        return jsonify({
            'id': url.id,
            'url': url.url,
            'title': url.title,
            'domain': url.domain,
            'path': url.path,
            'query_params': url.query_params,
            'tags': url.tags,
            'notes': url.notes,
            'created_at': url.created_at.isoformat(),
            'updated_at': url.updated_at.isoformat()
        }), 201
    except SQLAlchemyError as e:
        db.rollback()
        error_msg = f"Database error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()

@app.route('/extension/urls', methods=['GET'])
def get_urls():
    try:
        db = next(get_db())
        urls = db.query(URL).all()
        return jsonify([{
            'id': url.id,
            'url': url.url,
            'title': url.title,
            'domain': url.domain,
            'path': url.path,
            'query_params': url.query_params,
            'tags': url.tags if hasattr(url, 'tags') else [],
            'notes': url.notes if hasattr(url, 'notes') else '',
            'created_at': url.created_at.isoformat(),
            'updated_at': url.updated_at.isoformat()
        } for url in urls])
    except SQLAlchemyError as e:
        error_msg = f"Database error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()

@app.route('/extension/urls/<int:url_id>', methods=['GET'])
def get_url(url_id):
    try:
        db = next(get_db())
        url = db.query(URL).filter(URL.id == url_id).first()
        if not url:
            return jsonify({'error': 'URL not found'}), 404
        
        return jsonify({
            'id': url.id,
            'url': url.url,
            'title': url.title,
            'domain': url.domain,
            'path': url.path,
            'query_params': url.query_params,
            'tags': url.tags if hasattr(url, 'tags') else [],
            'notes': url.notes if hasattr(url, 'notes') else '',
            'created_at': url.created_at.isoformat(),
            'updated_at': url.updated_at.isoformat()
        })
    except SQLAlchemyError as e:
        error_msg = f"Database error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()

# 全局错误处理器
@app.errorhandler(Exception)
def handle_error(error):
    error_msg = f"Global error handler caught: {str(error)}\n{traceback.format_exc()}"
    logger.error(error_msg)
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # 初始化数据库
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        error_msg = f"Failed to initialize database: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        raise

    # 启动URL队列处理器
    url_queue.start()
    logger.info("URL queue processor started")

    # 启动URL处理工作线程
    url_worker.start()
    logger.info("URL worker started")

    # 启动服务器
    app.run(debug=True, port=8080, host='0.0.0.0') 
