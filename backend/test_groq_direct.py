from dotenv import load_dotenv
load_dotenv()
import os, time
import asyncio
from groq import AsyncGroq

async def test_groq():
    client = AsyncGroq(api_key=os.getenv('GROQ_API_KEY'))
    print('Client created. Calling API...')
    start = time.time()
    resp = await client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[{"role": "user", "content": 'Return this exact JSON: {"status": "ok"}'}],
        temperature=0.1
    )
    print(f'Response ({time.time()-start:.1f}s):', resp.choices[0].message.content)

if __name__ == '__main__':
    asyncio.run(test_groq())
