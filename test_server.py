import threading
import uvicorn
import time
import requests

def run_server():
    uvicorn.run('api:app', port=8000, host='127.0.0.1', log_level='critical')

if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(3)
    
    try:
        res_m = requests.get('http://127.0.0.1:8000/metrics/json', timeout=2)
        print("metrics:", res_m.status_code)
    except Exception as e:
        print("metrics error:", e)
        
    try:
        res_h = requests.get('http://127.0.0.1:8000/health', timeout=2)
        print("health:", res_h.status_code)
    except Exception as e:
        print("health error:", e)
