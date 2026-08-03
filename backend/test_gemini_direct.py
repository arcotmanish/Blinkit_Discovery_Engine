from dotenv import load_dotenv
load_dotenv()
import os, time
from google import genai
from google.genai import types

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
print('Client created. Calling API...')
start = time.time()
resp = client.models.generate_content(
    model='gemini-2.0-flash',
    contents='Return this exact JSON: {"status": "ok"}',
    config=types.GenerateContentConfig(response_mime_type='application/json', temperature=0.1)
)
print(f'Response ({time.time()-start:.1f}s):', resp.text)
