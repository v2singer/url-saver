from flask import Flask, request, jsonify
from flask_cors import CORS

from server.database import get_db, engine
from server.models import URL, Base
from server.url_queue import url_queue
from server.worker import url_worker
from server.config import ROLE, MASTER_HOST, MASTER_PORT, SLAVE_LIST, HOST, PORT

from sqlalchemy.exc import SQLAlchemyError
import logging
import traceback
import os
import jieba
import jieba.analyse
import threading
import time
import requests
from datetime import datetime

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

# --- 主从同步接口 ---

@app.route('/sync/url/push', methods=['POST'])
def sync_url_push():
    """主节点：接收从节点推送的url数据（支持批量）"""
    if ROLE != 'master':
        return jsonify({'error': 'Not master'}), 403
    data = request.get_json()
    if not data or 'urls' not in data:
        return jsonify({'error': 'urls required'}), 400
    urls = data['urls']
    db = next(get_db())
    count = 0
    for u in urls:
        # 以url字段为唯一键，存在则更新，不存在则插入
        obj = db.query(URL).filter(URL.url == u['url']).first()
        if obj:
            # 只更新比本地新的数据
            if 'updated_at' in u and u['updated_at'] > obj.updated_at.isoformat():
                for k, v in u.items():
                    if hasattr(obj, k):
                        setattr(obj, k, v)
                obj.updated_at = datetime.fromisoformat(u['updated_at'])
                count += 1
        else:
            # 新增
            new_url = URL(**u)
            if 'created_at' in u:
                new_url.created_at = datetime.fromisoformat(u['created_at'])
            if 'updated_at' in u:
                new_url.updated_at = datetime.fromisoformat(u['updated_at'])
            db.add(new_url)
            count += 1
    db.commit()
    db.close()
    return jsonify({'status': 'ok', 'updated': count})

@app.route('/sync/url/pull', methods=['GET'])
def sync_url_pull():
    """主节点：提供增量url数据，参数since=ISO8601时间字符串"""
    if ROLE != 'master':
        return jsonify({'error': 'Not master'}), 403
    since = request.args.get('since')
    db = next(get_db())
    q = db.query(URL)
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            q = q.filter(URL.updated_at > since_dt)
        except Exception:
            db.close()
            return jsonify({'error': 'invalid since'}), 400
    urls = q.all()
    result = []
    for u in urls:
        result.append({
            'url': u.url,
            'title': u.title,
            'domain': u.domain,
            'path': u.path,
            'query_params': u.query_params,
            'tags': u.tags,
            'notes': u.notes,
            'created_at': u.created_at.isoformat() if u.created_at else None,
            'updated_at': u.updated_at.isoformat() if u.updated_at else None
        })
    db.close()
    return jsonify({'urls': result})

# --- 从节点定时同步任务 ---
def slave_sync_loop():
    last_sync = None
    while True:
        try:
            db = next(get_db())
            # 1. 拉取主节点的增量数据
            params = {}
            if last_sync:
                params['since'] = last_sync
            resp = requests.get(f'http://{MASTER_HOST}:{MASTER_PORT}/sync/url/pull', params=params, timeout=5)
            if resp.ok:
                data = resp.json()
                for u in data.get('urls', []):
                    obj = db.query(URL).filter(URL.url == u['url']).first()
                    if obj:
                        if u['updated_at'] > obj.updated_at.isoformat():
                            for k, v in u.items():
                                if hasattr(obj, k):
                                    setattr(obj, k, v)
                            obj.updated_at = datetime.fromisoformat(u['updated_at'])
                    else:
                        new_url = URL(**u)
                        if 'created_at' in u:
                            new_url.created_at = datetime.fromisoformat(u['created_at'])
                        if 'updated_at' in u:
                            new_url.updated_at = datetime.fromisoformat(u['updated_at'])
                        db.add(new_url)
                db.commit()
                # 记录本次同步时间
                last_sync = datetime.utcnow().isoformat()
            # 2. 推送本地新增/变更数据到主节点
            q = db.query(URL)
            if last_sync:
                try:
                    since_dt = datetime.fromisoformat(last_sync)
                    q = q.filter(URL.updated_at > since_dt)
                except Exception:
                    pass
            urls = q.all()
            push_data = []
            for u in urls:
                push_data.append({
                    'url': u.url,
                    'title': u.title,
                    'domain': u.domain,
                    'path': u.path,
                    'query_params': u.query_params,
                    'tags': u.tags,
                    'notes': u.notes,
                    'created_at': u.created_at.isoformat() if u.created_at else None,
                    'updated_at': u.updated_at.isoformat() if u.updated_at else None
                })
            if push_data:
                try:
                    requests.post(f'http://{MASTER_HOST}:{MASTER_PORT}/sync/url/push', json={'urls': push_data}, timeout=5)
                except Exception:
                    pass
            db.close()
        except Exception:
            pass
        time.sleep(30)  # 每30秒同步一次

if __name__ == '__main__':
    # 初始化数据库
    SLAVE_LIST='192.168.100.174:8081'
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        error_msg = f"Failed to initialize database: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        raise

    # 启动URL队列处理器
    #url_queue.start()
    #logger.info("URL queue processor started")

    # 启动URL处理工作线程
    #url_worker.start()
    #logger.info("URL worker started")

    # 启动服务器
    print("starting server on %s:%d" % (HOST, PORT))
    app.run(debug=True, port=PORT, host=HOST)

    if ROLE == 'slave':
        t = threading.Thread(target=slave_sync_loop, daemon=True)
        t.start() 
