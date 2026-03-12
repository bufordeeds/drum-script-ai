#!/usr/bin/env python3
"""Test MuseScore CLI availability and functionality in the ML worker container"""

import subprocess
import shutil
import tempfile
import os

def test_musescore_cli():
    """Test if MuseScore CLI is available and working"""
    
    print("=== Testing MuseScore CLI Availability ===")
    
    # Check for MuseScore commands
    commands = ['mscore4portable', 'mscore4', 'mscore', 'musescore', 'musescore3']
    found_cmd = None
    
    for cmd in commands:
        path = shutil.which(cmd)
        if path:
            print(f"✓ Found {cmd} at: {path}")
            found_cmd = cmd
        else:
            print(f"✗ {cmd} not found")
    
    if not found_cmd:
        print("\n❌ No MuseScore CLI found!")
        return False
    
    print(f"\n=== Testing {found_cmd} ===")
    
    # Test basic command
    try:
        result = subprocess.run([found_cmd, '--version'], capture_output=True, text=True, timeout=10)
        print(f"Version check exit code: {result.returncode}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("❌ Version check timed out")
    except Exception as e:
        print(f"❌ Version check failed: {e}")
    
    # Test xvfb-run wrapper
    print("\n=== Testing with xvfb-run ===")
    try:
        result = subprocess.run([
            'xvfb-run', '-s', '-screen 0 640x480x24 -ac +extension GLX +render -noreset',
            found_cmd, '--version'
        ], capture_output=True, text=True, timeout=10)
        print(f"xvfb-run exit code: {result.returncode}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("❌ xvfb-run test timed out")
    except Exception as e:
        print(f"❌ xvfb-run test failed: {e}")
    
    # Test actual conversion
    print("\n=== Testing MusicXML Conversion ===")
    
    # Create a minimal MusicXML file
    musicxml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1">
      <part-name>Drums</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time>
          <beats>4</beats>
          <beat-type>4</beat-type>
        </time>
      </attributes>
      <note>
        <pitch>
          <step>C</step>
          <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
    
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as xml_temp:
        xml_temp.write(musicxml_content.encode('utf-8'))
        xml_temp_path = xml_temp.name
    
    try:
        # Test conversion to .mscx
        with tempfile.NamedTemporaryFile(suffix='.mscx', delete=False) as mscx_temp:
            mscx_temp_path = mscx_temp.name
        
        print(f"Converting {xml_temp_path} to {mscx_temp_path}")
        
        result = subprocess.run([
            'timeout', '30',
            'xvfb-run', '-s', '-screen 0 640x480x24 -ac +extension GLX +render -noreset',
            found_cmd, xml_temp_path, '-o', mscx_temp_path
        ], capture_output=True, text=True, timeout=35)
        
        print(f"Conversion exit code: {result.returncode}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        
        if os.path.exists(mscx_temp_path):
            size = os.path.getsize(mscx_temp_path)
            print(f"✓ MSCX file created: {size} bytes")
        else:
            print("✗ MSCX file not created")
        
        # Clean up
        for path in [xml_temp_path, mscx_temp_path]:
            if os.path.exists(path):
                os.unlink(path)
                
    except Exception as e:
        print(f"❌ Conversion test failed: {e}")
    
    return True

if __name__ == "__main__":
    # Run test inside the ML worker container
    print("Testing MuseScore CLI in ML worker container...")
    print("Run this command to test inside the container:")
    print("docker exec drum-script-ai-ml_worker-1 python /app/test_musescore.py")
    
    # For now, just test locally
    test_musescore_cli()