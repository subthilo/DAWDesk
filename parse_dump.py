import mido
import sys

def parse_dump(filename):
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Simple parsing of string representation of mido.Message
            print(line)
    except Exception as e:
        print(f"Error parsing dump: {e}")

if __name__ == '__main__':
    parse_dump('midi_dump.txt')
