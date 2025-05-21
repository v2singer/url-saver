from typing import Dict
from server.config import BaseOperator, register_operator, DOMAIN_CONFIGS, LUX_PATH, LUX_DOWNLOAD_PATH, FFMPEG_PATH, FFMPEG_OUTPUT_PATH
import logging
import subprocess
import os
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

@register_operator
class LuxOperator(BaseOperator):
    @property
    def name(self) -> str:
        return 'lux'
    
    def process(self, url: str, data: Dict) -> Dict:
        try:
            domain = urlparse(url).netloc
            if domain not in DOMAIN_CONFIGS:
                logger.warning(f"No configuration found for domain: {domain}")
                return data

            config = DOMAIN_CONFIGS[domain]
            lux_args = config.get('lux_args', [])
            
            # 构建完整的lux命令
            cmd = [LUX_PATH, url] + lux_args
            
            # 执行lux下载
            logger.info(f"Executing lux command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully downloaded content from {url}")
                data['lux_output'] = result.stdout
            else:
                logger.error(f"Lux download failed: {result.stderr}")
                data['error'] = result.stderr
            
            return data
        except Exception as e:
            logger.error(f"Error in LuxOperator: {str(e)}")
            data['error'] = str(e)
            return data

@register_operator
class FFmpegAudioOperator(BaseOperator):
    @property
    def name(self) -> str:
        return 'ffmpeg_audio'
    
    def process(self, url: str, data: Dict) -> Dict:
        try:
            domain = urlparse(url).netloc
            if domain not in DOMAIN_CONFIGS:
                logger.warning(f"No configuration found for domain: {domain}")
                return data

            config = DOMAIN_CONFIGS[domain]
            ffmpeg_args = config.get('ffmpeg_args', {}).get('audio', [])
            
            if not ffmpeg_args:
                logger.warning(f"No ffmpeg audio configuration found for domain: {domain}")
                return data

            # 从lux输出中获取输入文件路径
            input_file = data.get('lux_output', {}).get('file_path')
            if not input_file:
                logger.error("No input file found from lux output")
                return data

            # 构建输出文件路径
            output_filename = os.path.splitext(os.path.basename(input_file))[0] + '.mp3'
            output_path = os.path.join(FFMPEG_OUTPUT_PATH, output_filename)

            # 替换ffmpeg参数中的占位符
            cmd_args = []
            for arg in ffmpeg_args:
                if arg == '{input}':
                    cmd_args.append(input_file)
                elif arg == '{output}':
                    cmd_args.append(output_path)
                else:
                    cmd_args.append(arg)

            # 执行ffmpeg命令
            cmd = [FFMPEG_PATH] + cmd_args
            logger.info(f"Executing ffmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Successfully processed audio for {url}")
                data['ffmpeg_audio_output'] = output_path
            else:
                logger.error(f"FFmpeg audio processing failed: {result.stderr}")
                data['error'] = result.stderr

            return data
        except Exception as e:
            logger.error(f"Error in FFmpegAudioOperator: {str(e)}")
            data['error'] = str(e)
            return data

@register_operator
class FFmpegSubtitleOperator(BaseOperator):
    @property
    def name(self) -> str:
        return 'ffmpeg_subtitle'
    
    def process(self, url: str, data: Dict) -> Dict:
        try:
            domain = urlparse(url).netloc
            if domain not in DOMAIN_CONFIGS:
                logger.warning(f"No configuration found for domain: {domain}")
                return data

            config = DOMAIN_CONFIGS[domain]
            ffmpeg_args = config.get('ffmpeg_args', {}).get('subtitle', [])
            
            if not ffmpeg_args:
                logger.warning(f"No ffmpeg subtitle configuration found for domain: {domain}")
                return data

            # 从lux输出中获取输入文件路径
            input_file = data.get('lux_output', {}).get('file_path')
            if not input_file:
                logger.error("No input file found from lux output")
                return data

            # 构建输出文件路径
            output_filename = os.path.splitext(os.path.basename(input_file))[0] + '.srt'
            output_path = os.path.join(FFMPEG_OUTPUT_PATH, output_filename)

            # 替换ffmpeg参数中的占位符
            cmd_args = []
            for arg in ffmpeg_args:
                if arg == '{input}':
                    cmd_args.append(input_file)
                elif arg == '{output}':
                    cmd_args.append(output_path)
                else:
                    cmd_args.append(arg)

            # 执行ffmpeg命令
            cmd = [FFMPEG_PATH] + cmd_args
            logger.info(f"Executing ffmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"Successfully extracted subtitle for {url}")
                data['ffmpeg_subtitle_output'] = output_path
            else:
                logger.error(f"FFmpeg subtitle extraction failed: {result.stderr}")
                data['error'] = result.stderr

            return data
        except Exception as e:
            logger.error(f"Error in FFmpegSubtitleOperator: {str(e)}")
            data['error'] = str(e)
            return data

# Add more operators as needed
# Example:
# @register_operator
# class YouTubeOperator(BaseOperator):
#     @property
#     def name(self) -> str:
#         return 'youtube'
#     
#     def process(self, url: str, data: Dict) -> Dict:
#         # Implementation here
#         return data 