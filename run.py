import os
import sys
import uvicorn

_this_dir = os.path.dirname(os.path.abspath(__file__))
if _this_dir not in sys.path:
    sys.path.insert(0, _this_dir)
os.chdir(_this_dir)

if __name__ == "__main__":
    uvicorn.run(
        "oskar.api.app:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
