from alembic.config import Config
from alembic import command
import os

def run_migration():
    # 获取当前文件所在目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建 Alembic 配置
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", current_dir)
    alembic_cfg.set_main_option("sqlalchemy.url", "sqlite:///../urls.db")
    
    # 运行迁移
    command.upgrade(alembic_cfg, "head")

if __name__ == "__main__":
    run_migration() 