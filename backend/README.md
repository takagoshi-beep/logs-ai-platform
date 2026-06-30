# LOGS AI OS Backend V0.1

## Run

1. Create environment and install:

   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt

2. Start API:

   uvicorn main:app --reload --port 8000

3. Health check:

   http://localhost:8000/api/health

Product analytics events are appended to:

- backend/data/events.jsonl
