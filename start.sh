#!/bin/bash
# 启动脚本，自动导出config.py中的环境变量

# 数据库配置
export DATABASE_URL="sqlite:///./urls.db"

# Lux配置
export LUX_PATH="/usr/local/bin/lux"
export LUX_DOWNLOAD_PATH="./downloads"
export LUX_COOKIES_PATH="./cookies"

# FFmpeg配置
export FFMPEG_PATH="/usr/local/bin/ffmpeg"
export FFMPEG_OUTPUT_PATH="./processed"

# 向量数据库配置
export CHROMA_DB_PATH="./chroma_db"
export EMBEDDING_MODEL="all-MiniLM-L6-v2"

# 任务处理配置
export MAX_RETRY_COUNT="3"

# 主从同步配置
export ROLE="master"
export MASTER_HOST="127.0.0.1"
export MASTER_PORT="8080"
export SLAVE_LIST=""

EXEC_PATH="python"

# 安装依赖（如未安装）
#pip install -r server/requirements.txt

# 启动主程序
python -m server.main