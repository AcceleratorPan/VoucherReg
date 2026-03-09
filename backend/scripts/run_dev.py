"""Simple Python wrapper to start the development server.

Usage:

    # activate project environment first (conda or venv):
    conda activate C:\\Users\\90617\\Desktop\\abstract\\pku_task\\.conda
    python scripts/run_dev.py

This avoids shell‐specific issues with `run_dev.sh` and ensures the
correct Python interpreter is used.  The script simply invokes
uvicorn programmatically.
"""

import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
