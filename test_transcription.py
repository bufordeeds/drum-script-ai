#!/usr/bin/env python3
"""Test transcription with debug output"""

import os
import sys
import subprocess

# First install requests
subprocess.run([sys.executable, "-m", "pip", "install", "requests", "numpy", "scipy"], check=True)

import requests
import time
import json
import numpy as np
from scipy.io import wavfile

# API configuration
API_BASE_URL = "http://localhost:8000/api/v1"

def create_test_audio():
    """Create a simple test audio file"""
    sample_rate = 44100
    duration = 5  # 5 seconds
    t = np.linspace(0, duration, sample_rate * duration)
    
    # Simple drum pattern simulation
    audio = np.zeros_like(t)
    
    # Add some drum hits
    for i in range(5):
        hit_time = i * sample_rate
        if hit_time < len(audio):
            # Simple exponential decay envelope
            envelope = np.exp(-10 * np.arange(sample_rate) / sample_rate)
            noise = np.random.normal(0, 0.1, len(envelope))
            audio[hit_time:hit_time + len(envelope)] += envelope * noise
    
    # Normalize
    audio = np.int16(audio / np.max(np.abs(audio)) * 32767)
    
    # Save as WAV
    test_file = "test_drums.wav"
    wavfile.write(test_file, sample_rate, audio)
    print(f"✓ Created test audio file: {test_file}")
    return test_file

def test_transcription():
    """Test the transcription workflow"""
    
    # Create test audio
    audio_file = create_test_audio()
    
    # Upload file
    print("\n1. Uploading audio file...")
    with open(audio_file, 'rb') as f:
        files = {'file': (audio_file, f, 'audio/wav')}
        response = requests.post(f"{API_BASE_URL}/transcription/upload", files=files)
    
    if response.status_code != 200:
        print(f"❌ Upload failed: {response.status_code}")
        print(response.text)
        return
    
    job_data = response.json()
    job_id = job_data['job_id']
    print(f"✓ Job created: {job_id}")
    
    # Poll for status
    print("\n2. Processing...")
    max_wait = 120  # 2 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        response = requests.get(f"{API_BASE_URL}/transcription/jobs/{job_id}/status")
        status_data = response.json()
        
        status = status_data.get('status')
        progress = status_data.get('progress', 0)
        stage = status_data.get('current_stage', '')
        
        print(f"\r  Status: {status} | Progress: {progress}% | Stage: {stage}".ljust(80), end='')
        
        if status == 'completed':
            print("\n✓ Processing completed!")
            break
        elif status == 'error':
            print(f"\n❌ Processing failed: {status_data.get('error_message')}")
            return
        
        time.sleep(2)
    else:
        print("\n❌ Timeout waiting for completion")
        return
    
    # Get result
    print("\n3. Getting result...")
    response = requests.get(f"{API_BASE_URL}/transcription/jobs/{job_id}/result")
    result_data = response.json()
    
    print(f"✓ Result retrieved")
    print(f"  Download URLs: {json.dumps(result_data.get('download_urls', {}), indent=2)}")
    
    # Check which exports are available
    print("\n4. Checking exports...")
    for format_type in ['musicxml', 'midi', 'pdf', 'mscx', 'mscz']:
        url = result_data.get('download_urls', {}).get(format_type)
        if url:
            print(f"  ✓ {format_type}: {url}")
        else:
            print(f"  ✗ {format_type}: Not available")
    
    # Clean up
    os.remove(audio_file)

if __name__ == "__main__":
    test_transcription()