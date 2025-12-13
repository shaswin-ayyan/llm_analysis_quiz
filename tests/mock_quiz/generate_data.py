import os
import csv
import zipfile
import random
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def generate_csv():
    """Generates a CSV with dirty data."""
    filepath = os.path.join(STATIC_DIR, "complex_data.csv")
    print(f"Generating {filepath}...")
    
    headers = ["ID", "Category", "Score", "Date", "Notes"]
    categories = ["A", "B", "C", "A", "B"]
    
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        
        for i in range(1, 101):
            cat = random.choice(categories)
            # Dirty score: mix of ints, floats, and currency strings
            if i % 10 == 0:
                score = "NaN"
            elif i % 5 == 0:
                score = f"${random.randint(100, 1000)}"
            else:
                score = random.randint(50, 100)
                
            date = f"2023-01-{i%30+1:02d}"
            notes = f"Note {i}"
            
            writer.writerow([i, cat, score, date, notes])

def generate_archive():
    """Generates a ZIP file with nested folders and a secret."""
    filepath = os.path.join(STATIC_DIR, "archive.zip")
    print(f"Generating {filepath}...")
    
    # Create a temporary directory for structure
    temp_dir = os.path.join(STATIC_DIR, "temp_archive")
    ensure_dir(temp_dir)
    
    # Structure:
    # /level1
    #   /level2
    #     secret.txt (contains the key)
    #   noise.txt
    
    l1 = os.path.join(temp_dir, "level1")
    l2 = os.path.join(l1, "level2")
    ensure_dir(l2)
    
    with open(os.path.join(l2, "secret.txt"), "w") as f:
        f.write("The secret key is: SUPER_SECRET_KEY_123")
        
    with open(os.path.join(l1, "noise.txt"), "w") as f:
        f.write("Just some noise here.")
        
    # Zip it
    with zipfile.ZipFile(filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, temp_dir)
                zipf.write(file_path, arcname)
                
    # Cleanup
    shutil.rmtree(temp_dir)

def generate_audio():
    """Generates a simple WAV file."""
    filepath = os.path.join(STATIC_DIR, "challenge.wav")
    print(f"Generating {filepath}...")
    
    import wave
    import math
    import struct
    
    sample_rate = 44100
    duration = 2.0 # seconds
    frequency = 440.0 # Hz
    
    with wave.open(filepath, 'w') as obj:
        obj.setnchannels(1) # mono
        obj.setsampwidth(2) # 2 bytes
        obj.setframerate(sample_rate)
        
        for i in range(int(sample_rate * duration)):
            value = int(32767.0 * math.sin(frequency * math.pi * 2 * i / sample_rate))
            data = struct.pack('<h', value)
            obj.writeframesraw(data)

def main():
    ensure_dir(STATIC_DIR)
    generate_csv()
    generate_archive()
    generate_audio()
    print("Data generation complete.")

if __name__ == "__main__":
    main()
