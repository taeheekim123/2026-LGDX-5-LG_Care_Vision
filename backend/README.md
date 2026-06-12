# Backend

FastAPI backend for the LG Care Shot prototype.

## Run

```powershell
cd "C:\dx_team\my-app\backend"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```
