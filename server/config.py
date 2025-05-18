import os
from dotenv import load_dotenv

load_dotenv()

# Use SQLite database
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./urls.db')

# Lux配置
LUX_PATH = os.getenv('LUX_PATH', '/usr/local/bin/lux')  # lux程序路径
LUX_DOWNLOAD_PATH = os.getenv('LUX_DOWNLOAD_PATH', './downloads')  # 下载文件保存路径
LUX_COOKIES_PATH = os.getenv('LUX_COOKIES_PATH', './cookies')  # cookies文件路径

# FFmpeg配置
FFMPEG_PATH = os.getenv('FFMPEG_PATH', '/usr/local/bin/ffmpeg')  # ffmpeg程序路径
FFMPEG_OUTPUT_PATH = os.getenv('FFMPEG_OUTPUT_PATH', './processed')  # ffmpeg处理后的文件保存路径

# 向量数据库配置
CHROMA_DB_PATH = os.getenv('CHROMA_DB_PATH', './chroma_db')  # Chroma数据库路径
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')  # 向量模型名称

# 任务处理配置
MAX_RETRY_COUNT = int(os.getenv('MAX_RETRY_COUNT', '3'))  # 最大重试次数，-1表示无限重试

# 域名特定配置
DOMAIN_CONFIGS = {
    'bilibili.com': {
        'lux_args': [
            #'-c', LUX_COOKIES_PATH,  # cookies文件
            '-o', LUX_DOWNLOAD_PATH,  # 输出目录
            '-eto',
        ],
        'ffmpeg_args': {
            'audio': [
                '-i', '{input}',  # 输入文件
                '-vn',  # 不处理视频
                '-acodec', 'libmp3lame',  # 音频编码器
                '-q:a', '2',  # 音频质量
                '{output}'  # 输出文件
            ],
            'subtitle': [
                '-i', '{input}',  # 输入文件
                '-map', '0:s:0',  # 选择第一个字幕流
                '{output}'  # 输出文件
            ]
        },
        'process_chain': ['lux', 'ffmpeg_audio', 'ffmpeg_subtitle']  # 处理链顺序
    }
} 