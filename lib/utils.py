from dotenv import load_dotenv
import os

def get_play_path(boxes):
    return [(d['result'], d['value'])
            for t in boxes for d in t
            if d['result'] != None]

if __name__ == '__main__':
    load_dotenv()
    print(os.getenv('MONGO_HOST'))
    # do cool stuffs
