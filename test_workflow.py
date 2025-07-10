#!/usr/bin/env python3
"""
Test script to validate the complete drum transcription workflow
"""

import requests
import time
import json
import sys
import os
from pathlib import Path

# API configuration
API_BASE_URL = "http://localhost:8000/api/v1"

def check_health():
    """Check if the API is healthy"""
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            health_data = response.json()
            print("✅ Health check passed")
            print(f"   Status: {health_data.get('status')}")
            print(f"   Checks: {health_data.get('checks')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def create_test_audio():
    """Create a simple test audio file using numpy and scipy"""
    try:
        import numpy as np
        from scipy.io import wavfile
        
        # Generate a simple drum pattern (kick and snare simulation)
        sample_rate = 44100
        duration = 5  # 5 seconds
        t = np.linspace(0, duration, sample_rate * duration)
        
        # Simple drum pattern simulation
        # Kick drum (low frequency pulse every beat)
        kick_freq = 60
        kick_pattern = np.zeros_like(t)
        for beat in [0, 1, 2, 3, 4]:  # 5 beats
            beat_time = beat * sample_rate
            if beat_time < len(kick_pattern):
                kick_pattern[beat_time:beat_time + 1000] = np.sin(2 * np.pi * kick_freq * t[beat_time:beat_time + 1000]) * 0.5
        
        # Snare drum (mid frequency noise burst)
        snare_pattern = np.zeros_like(t)
        for beat in [0.5, 1.5, 2.5, 3.5, 4.5]:  # Off-beats
            beat_time = int(beat * sample_rate)
            if beat_time < len(snare_pattern) - 2000:
                noise = np.random.normal(0, 0.1, 2000)
                snare_pattern[beat_time:beat_time + 2000] = noise * 0.3
        
        # Combine patterns
        audio = kick_pattern + snare_pattern
        audio = np.clip(audio, -1, 1)  # Normalize
        
        # Convert to 16-bit int
        audio_int = (audio * 32767).astype(np.int16)
        
        # Save as WAV file
        test_file = "test_drum_pattern.wav"
        wavfile.write(test_file, sample_rate, audio_int)
        
        print(f"✅ Created test audio file: {test_file}")
        return test_file
        
    except ImportError:
        print("❌ scipy/numpy not available. Using existing audio file.")
        return None
    except Exception as e:
        print(f"❌ Error creating test audio: {e}")
        return None

def upload_file(file_path):
    """Upload an audio file for transcription"""
    try:
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return None
            
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'audio/wav')}
            response = requests.post(f"{API_BASE_URL}/transcription/upload", files=files)
        
        if response.status_code == 200:
            upload_data = response.json()
            job_id = upload_data['jobId']
            print(f"✅ File uploaded successfully")
            print(f"   Job ID: {job_id}")
            print(f"   Status: {upload_data['status']}")
            return job_id
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def monitor_job(job_id):
    """Monitor job progress until completion"""
    print(f"\n📊 Monitoring job {job_id}...")
    
    max_attempts = 60  # 5 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(f"{API_BASE_URL}/transcription/jobs/{job_id}")
            
            if response.status_code == 200:
                job_data = response.json()
                status = job_data['status']
                progress = job_data['progress']
                stage = job_data.get('stage', 'unknown')
                
                print(f"   Status: {status} | Progress: {progress}% | Stage: {stage}")
                
                if status == 'completed':
                    print("✅ Job completed successfully!")
                    return True
                elif status == 'error':
                    error_msg = job_data.get('errorMessage', 'Unknown error')
                    print(f"❌ Job failed: {error_msg}")
                    return False
                
                time.sleep(5)  # Check every 5 seconds
                attempt += 1
                
            else:
                print(f"❌ Failed to get job status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error monitoring job: {e}")
            return False
    
    print("❌ Job monitoring timed out")
    return False

def test_exports(job_id):
    """Test downloading export files"""
    formats = ['musicxml', 'midi', 'pdf']
    results = {}
    
    for format_type in formats:
        try:
            response = requests.get(f"{API_BASE_URL}/export/{format_type}/{job_id}")
            
            if response.status_code == 200:
                # Save the file
                filename = f"test_export.{format_type}"
                with open(filename, 'wb') as f:
                    f.write(response.content)
                
                file_size = len(response.content)
                print(f"✅ {format_type.upper()} export: {file_size} bytes saved to {filename}")
                results[format_type] = True
            else:
                print(f"❌ {format_type.upper()} export failed: {response.status_code}")
                results[format_type] = False
                
        except Exception as e:
            print(f"❌ {format_type.upper()} export error: {e}")
            results[format_type] = False
    
    return results

def cleanup_test_files():
    """Clean up test files"""
    test_files = [
        "test_drum_pattern.wav",
        "test_export.musicxml",
        "test_export.midi", 
        "test_export.pdf"
    ]
    
    for file_path in test_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🧹 Cleaned up: {file_path}")
        except Exception as e:
            print(f"⚠️  Failed to clean up {file_path}: {e}")

def main():
    """Main test workflow"""
    print("🎵 Starting Drum Transcription Service Test\n")
    
    # Step 1: Health check
    print("1️⃣ Checking API health...")
    if not check_health():
        print("❌ API is not healthy. Make sure services are running.")
        sys.exit(1)
    
    # Step 2: Create or find test audio
    print("\n2️⃣ Preparing test audio...")
    test_file = create_test_audio()
    
    if not test_file:
        # Look for existing audio files
        audio_extensions = ['.wav', '.mp3', '.m4a']
        current_dir = Path('.')
        for ext in audio_extensions:
            audio_files = list(current_dir.glob(f'*{ext}'))
            if audio_files:
                test_file = str(audio_files[0])
                print(f"✅ Using existing audio file: {test_file}")
                break
        
        if not test_file:
            print("❌ No audio file available for testing")
            print("   Please create a test audio file or install scipy/numpy")
            sys.exit(1)
    
    # Step 3: Upload file
    print("\n3️⃣ Uploading audio file...")
    job_id = upload_file(test_file)
    if not job_id:
        sys.exit(1)
    
    # Step 4: Monitor processing
    print("\n4️⃣ Monitoring transcription...")
    if not monitor_job(job_id):
        sys.exit(1)
    
    # Step 5: Test exports
    print("\n5️⃣ Testing export downloads...")
    export_results = test_exports(job_id)
    
    # Step 6: Results summary
    print("\n📋 Test Results Summary:")
    print("=" * 40)
    
    all_passed = True
    tests = [
        ("Health Check", True),
        ("File Upload", job_id is not None),
        ("Processing", True),  # If we got here, processing worked
        ("MusicXML Export", export_results.get('musicxml', False)),
        ("MIDI Export", export_results.get('midi', False)),
        ("PDF Export", export_results.get('pdf', False))
    ]
    
    for test_name, passed in tests:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 40)
    
    if all_passed:
        print("🎉 All tests passed! The drum transcription service is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    # Step 7: Cleanup
    print("\n6️⃣ Cleaning up test files...")
    cleanup_test_files()
    
    print("\n✨ Test completed!")

if __name__ == "__main__":
    main()