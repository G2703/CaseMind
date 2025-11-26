import asyncio
import logging
import sys
from pathlib import Path
from pathlib import Path as P

# Ensure src is on sys.path
sys.path.insert(0, str(P(__file__).resolve().parents[1] / 'src'))

from pipelines.ingestion_pipeline import DataIngestionPipeline



logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def run():
    pipeline = DataIngestionPipeline()
    result = await pipeline.process_batch(Path('cases/test_ingest'))
    print('\nBatch Result:')
    print(result)

if __name__ == '__main__':
    asyncio.run(run())
