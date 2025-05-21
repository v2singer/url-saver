import json
import time
import os
from loguru import logger
import requests
from dotenv import load_dotenv
import numpy as np
import soundfile as sf
from utils import save_wav

# Ensure numpy is properly initialized
#np._import_array()

load_dotenv()

WHISPERX_SERVICE_URL = os.getenv('WHISPERX_SERVICE_URL', 'http://localhost:8000')

def transcribe_audio(folder, model_name: str = 'large', device='auto', batch_size=32, diarization=True, min_speakers=None, max_speakers=None):
    if os.path.exists(os.path.join(folder, 'transcript.json')):
        logger.info(f'Transcript already exists in {folder}')
        return True
    
    wav_path = os.path.join(folder, 'audio_vocals.wav')
    if not os.path.exists(wav_path):
        return False
    
    logger.info(f'Transcribing {wav_path}')
    
    try:
        # Prepare request data
        request_data = {
            'model_name': model_name,
            'device': device,
            'batch_size': batch_size,
            'diarization': diarization,
            'min_speakers': min_speakers,
            'max_speakers': max_speakers,
        }
        
        # Prepare files for upload
        files = {
            'file': ('audio_vocals.wav', open(wav_path, 'rb'), 'audio/wav')
        }
        
        # Send request to WhisperX service with file upload
        response = requests.post(
            f"{WHISPERX_SERVICE_URL}/transcribe",
            data=request_data,
            files=files
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Process the response
        transcript = [{
            'start': segment['start'],
            'end': segment['end'],
            'text': segment['text'].strip(),
            'speaker': segment.get('speaker', 'SPEAKER_00')
        } for segment in result['segments']]
        
        transcript = merge_segments(transcript)
        
        # Save transcript
        with open(os.path.join(folder, 'transcript.json'), 'w', encoding='utf-8') as f:
            json.dump(transcript, f, indent=4, ensure_ascii=False)
        
        logger.info(f'Transcribed {wav_path} successfully, and saved to {os.path.join(folder, "transcript.json")}')
        generate_speaker_audio(folder, transcript)
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error calling WhisperX service: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error processing transcription: {str(e)}")
        return False
    finally:
        # Ensure the file is closed
        if 'files' in locals():
            files['file'][1].close()

def merge_segments(transcript, ending='!"\').:;?]}~'):
    merged_transcription = []
    buffer_segment = None

    for segment in transcript:
        if buffer_segment is None:
            buffer_segment = segment
        else:
            if buffer_segment['text'][-1] in ending:
                merged_transcription.append(buffer_segment)
                buffer_segment = segment
            else:
                buffer_segment['text'] += ' ' + segment['text']
                buffer_segment['end'] = segment['end']

    if buffer_segment is not None:
        merged_transcription.append(buffer_segment)

    return merged_transcription

def generate_speaker_audio(folder, transcript):
    wav_path = os.path.join(folder, 'audio_vocals.wav')
    # Use soundfile instead of librosa
    audio_data, samplerate = sf.read(wav_path)
    
    # Convert to mono if stereo
    if len(audio_data.shape) > 1:
        audio_data = audio_data.mean(axis=1)
    
    speaker_dict = dict()
    length = len(audio_data)
    delay = 0.05
    
    for segment in transcript:
        start = max(0, int((segment['start'] - delay) * samplerate))
        end = min(int((segment['end']+delay) * samplerate), length)
        speaker_segment_audio = audio_data[start:end]
        
        # Convert to float32 to ensure compatibility
        speaker_segment_audio = speaker_segment_audio.astype(np.float32)
        
        # Initialize empty array if speaker not in dict
        if segment['speaker'] not in speaker_dict:
            speaker_dict[segment['speaker']] = np.array([], dtype=np.float32)
            
        # Safely concatenate arrays
        speaker_dict[segment['speaker']] = np.concatenate([
            speaker_dict[segment['speaker']],
            speaker_segment_audio
        ])

    speaker_folder = os.path.join(folder, 'SPEAKER')
    if not os.path.exists(speaker_folder):
        os.makedirs(speaker_folder)
    
    for speaker, audio in speaker_dict.items():
        speaker_file_path = os.path.join(
            speaker_folder, f"{speaker}.wav")
        # Ensure audio is float32 before saving
        audio = audio.astype(np.float32)
        save_wav(audio, speaker_file_path)

def transcribe_all_audio_under_folder(folder, model_name: str = 'large', device='auto', batch_size=32, diarization=True, min_speakers=None, max_speakers=None):
    for root, dirs, files in os.walk(folder):
        if 'audio_vocals.wav' in files and 'transcript.json' not in files:
            transcribe_audio(root, model_name, device, batch_size, diarization, min_speakers, max_speakers)
    return f'Transcribed all audio under {folder}'

if __name__ == '__main__':
    #transcribe_all_audio_under_folder('videos')
    transcribe_all_audio_under_folder('downloaded')
    #with open('downloaded/transcript.json', 'r') as f:
    #    transcript = json.load(f)
    #generate_speaker_audio("downloaded", transcript)
    
    
