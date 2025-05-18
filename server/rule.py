import subprocess
import logging
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from server.config import LUX_PATH, FFMPEG_PATH, LUX_DOWNLOAD_PATH, FFMPEG_OUTPUT_PATH, DOMAIN_CONFIGS, MAX_RETRY_COUNT
from server.database import get_db
from server.models import Task, TaskStatus, ProcessingStage

logger = logging.getLogger(__name__)

class URLProcessor:
    def __init__(self):
        self.processors = {
            'bilibili.com': self._process_bilibili,
            'www.bilibili.com': self._process_bilibili,
        }
        # 确保输出目录存在
        os.makedirs(LUX_DOWNLOAD_PATH, exist_ok=True)
        os.makedirs(FFMPEG_OUTPUT_PATH, exist_ok=True)

    def _create_temp_dir(self, url):
        """为URL创建临时目录"""
        # 使用URL的哈希值作为临时目录名
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        temp_dir = os.path.join(LUX_DOWNLOAD_PATH, f"temp_{url_hash}")
        os.makedirs(temp_dir, exist_ok=True)
        return temp_dir

    def _check_download_success(self, temp_dir):
        """检查临时目录中是否存在MP4文件"""
        mp4_files = list(Path(temp_dir).glob('*.mp4'))
        return len(mp4_files) > 0, mp4_files[0] if mp4_files else None

    def _update_task_status(self, url, status, error_message=None, result_data=None, stage=None):
        """更新任务状态"""
        try:
            db = next(get_db())
            task = db.query(Task).filter(Task.url == url).first()
            if task:
                task.status = status
                if error_message:
                    task.error_message = error_message
                if result_data:
                    task.result_data = result_data
                if stage:
                    task.current_stage = stage
                if status == TaskStatus.PROCESSING:
                    task.started_at = datetime.utcnow()
                elif status in [TaskStatus.SUCCESS, TaskStatus.FAILED]:
                    task.completed_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.error(f"Error updating task status: {str(e)}")
        finally:
            db.close()

    def _get_task_stage(self, url):
        """获取任务的当前处理阶段"""
        try:
            db = next(get_db())
            task = db.query(Task).filter(Task.url == url).first()
            return task.current_stage if task else ProcessingStage.INIT
        except Exception as e:
            logger.error(f"Error getting task stage: {str(e)}")
            return ProcessingStage.INIT
        finally:
            db.close()

    def process_url(self, url):
        """处理URL的主入口"""
        try:
            # 获取当前处理阶段
            current_stage = self._get_task_stage(url)
            
            # 更新任务状态为处理中
            self._update_task_status(url, TaskStatus.PROCESSING, stage=current_stage)
            
            # 从URL中提取域名
            domain = url.split('/')[2]
            
            # 查找对应的处理器
            processor = self.processors.get(domain)
            if processor:
                result = processor(url, current_stage)
                if result:
                    self._update_task_status(url, TaskStatus.SUCCESS)
                else:
                    self._update_task_status(url, TaskStatus.FAILED, "Processing failed")
                return result
            else:
                error_msg = f"No processor found for domain: {domain}"
                logger.warning(error_msg)
                self._update_task_status(url, TaskStatus.FAILED, error_msg)
                return False
        except Exception as e:
            error_msg = f"Error processing URL {url}: {str(e)}"
            logger.error(error_msg)
            self._update_task_status(url, TaskStatus.FAILED, error_msg)
            return False

    def _run_command(self, cmd, description):
        """执行命令并返回结果"""
        try:
            logger.info(f"Executing {description}: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully completed {description}")
                logger.debug(f"Command output: {result.stdout}")
                return True, result.stdout
            else:
                logger.error(f"Failed to complete {description}")
                logger.error(f"Error output: {result.stderr}")
                return False, result.stderr
        except Exception as e:
            logger.error(f"Error executing {description}: {str(e)}")
            return False, str(e)

    def _process_bilibili(self, url, start_stage=ProcessingStage.INIT):
        """处理bilibili.com的URL"""
        try:
            # 获取bilibili的特定配置
            config = DOMAIN_CONFIGS['bilibili.com']
            input_file = None
            temp_dir = None
            result_data = {}
            
            # 执行处理链
            for processor in config['process_chain']:
                # 检查是否需要跳过当前处理阶段
                if processor == 'lux' and start_stage != ProcessingStage.INIT:
                    continue
                elif processor == 'ffmpeg_audio' and start_stage not in [ProcessingStage.INIT, ProcessingStage.DOWNLOAD]:
                    continue
                elif processor == 'ffmpeg_subtitle' and start_stage not in [ProcessingStage.INIT, ProcessingStage.DOWNLOAD, ProcessingStage.AUDIO_EXTRACT]:
                    continue
                elif processor == 'vectorize' and start_stage not in [ProcessingStage.INIT, ProcessingStage.DOWNLOAD, ProcessingStage.AUDIO_EXTRACT, ProcessingStage.SUBTITLE_EXTRACT]:
                    continue

                if processor == 'lux':
                    # 更新处理阶段
                    self._update_task_status(url, TaskStatus.PROCESSING, stage=ProcessingStage.DOWNLOAD)
                    
                    # 创建临时目录
                    temp_dir = self._create_temp_dir(url)
                    
                    # 修改lux参数以使用临时目录
                    lux_args = config['lux_args'].copy()
                    for i, arg in enumerate(lux_args):
                        if arg == '-o':
                            lux_args[i + 1] = temp_dir
                    
                    # 执行Lux下载
                    cmd = [LUX_PATH] + lux_args + [url]
                    success, output = self._run_command(cmd, "Lux download")
                    if not success:
                        return False
                    
                    # 检查下载是否成功
                    download_success, downloaded_file = self._check_download_success(temp_dir)
                    if not download_success:
                        logger.error("No MP4 files found in temporary directory")
                        return False
                    
                    input_file = str(downloaded_file)
                    result_data['video_file'] = input_file
                    
                elif processor == 'ffmpeg_audio':
                    # 更新处理阶段
                    self._update_task_status(url, TaskStatus.PROCESSING, stage=ProcessingStage.AUDIO_EXTRACT)
                    
                    if not input_file:
                        logger.error("No input file for audio extraction")
                        return False
                        
                    # 准备输出文件路径
                    input_filename = os.path.basename(input_file)
                    output_file = os.path.join(FFMPEG_OUTPUT_PATH, f"audio_{os.path.splitext(input_filename)[0]}.mp3")
                    
                    # 构建ffmpeg命令
                    ffmpeg_cmd = [FFMPEG_PATH]
                    for arg in config['ffmpeg_args']['audio']:
                        if arg == '{input}':
                            ffmpeg_cmd.append(input_file)
                        elif arg == '{output}':
                            ffmpeg_cmd.append(output_file)
                        else:
                            ffmpeg_cmd.append(arg)
                    
                    # 执行ffmpeg处理
                    success, output = self._run_command(ffmpeg_cmd, "FFmpeg audio extraction")
                    if not success:
                        return False
                    
                    result_data['audio_file'] = output_file
                    
                elif processor == 'ffmpeg_subtitle':
                    # 更新处理阶段
                    self._update_task_status(url, TaskStatus.PROCESSING, stage=ProcessingStage.SUBTITLE_EXTRACT)
                    
                    if not input_file:
                        logger.error("No input file for subtitle extraction")
                        return False
                        
                    # 准备输出文件路径
                    input_filename = os.path.basename(input_file)
                    output_file = os.path.join(FFMPEG_OUTPUT_PATH, f"subtitle_{os.path.splitext(input_filename)[0]}.srt")
                    
                    # 构建ffmpeg命令
                    ffmpeg_cmd = [FFMPEG_PATH]
                    for arg in config['ffmpeg_args']['subtitle']:
                        if arg == '{input}':
                            ffmpeg_cmd.append(input_file)
                        elif arg == '{output}':
                            ffmpeg_cmd.append(output_file)
                        else:
                            ffmpeg_cmd.append(arg)
                    
                    # 执行ffmpeg处理
                    success, output = self._run_command(ffmpeg_cmd, "FFmpeg subtitle extraction")
                    if not success:
                        return False
                    
                    # 保存字幕文件路径供后续处理使用
                    subtitle_file = output_file
                    result_data['subtitle_file'] = subtitle_file
                    
                elif processor == 'vectorize':
                    # 更新处理阶段
                    self._update_task_status(url, TaskStatus.PROCESSING, stage=ProcessingStage.VECTORIZE)
                    
                    from server.vector_store import vector_store
                    if not subtitle_file or not os.path.exists(subtitle_file):
                        logger.error("No subtitle file for vectorization")
                        return False
                        
                    # 读取字幕文件
                    with open(subtitle_file, 'r', encoding='utf-8') as f:
                        subtitle_text = f.read()
                    
                    # 提取视频ID（从文件名中）
                    video_id = os.path.splitext(os.path.basename(input_file))[0]
                    
                    # 添加到向量数据库
                    metadata = {
                        'video_id': video_id,
                        'url': url,
                        'source_file': input_file,
                        'subtitle_file': subtitle_file
                    }
                    
                    success = vector_store.add_subtitle(video_id, subtitle_text, metadata)
                    if not success:
                        logger.error("Failed to add subtitle to vector store")
                        return False
                    
                    result_data['video_id'] = video_id
            
            # 清理临时目录
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            
            # 更新任务状态和结果数据
            self._update_task_status(url, TaskStatus.SUCCESS, result_data=result_data)
            return True
                
        except Exception as e:
            logger.error(f"Error in bilibili processor: {str(e)}")
            # 确保在发生错误时也清理临时目录
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return False

# 创建全局处理器实例
url_processor = URLProcessor() 