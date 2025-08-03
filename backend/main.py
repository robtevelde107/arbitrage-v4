"""
Launcher script for the arbitrage backend.

You can run this module directly with Python to start the FastAPI server.
For production deployments, consider using a process manager like Gunicorn
with Uvicorn workers. PythonAnywhere can run this as a WSGI/ASGI app.
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
