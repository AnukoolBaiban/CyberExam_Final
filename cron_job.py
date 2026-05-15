"""
cron_job.py  —  Keep-Alive Traffic Simulator
Run this locally or via GitHub Actions every 10 minutes to prevent
Streamlit Cloud from putting the app to sleep.

Usage:
    python cron_job.py --url https://<your-app>.streamlit.app

GitHub Actions example (.github/workflows/keepalive.yml):
    on:
      schedule:
        - cron: '*/10 * * * *'
    jobs:
      ping:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v3
          - run: python cron_job.py --url ${{ secrets.APP_URL }}

UptimeRobot:
    Monitor Type : HTTP(s)
    URL          : https://<your-app>.streamlit.app
    Interval     : 10 minutes
"""

import argparse
import urllib.request
import urllib.error
import json
import time
import datetime

def ping(url: str, timeout: int = 30) -> dict:
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "KMUTT-KeepAlive/1.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
        result = {"ts": ts, "url": url, "status": status, "ok": True}
    except urllib.error.HTTPError as e:
        result = {"ts": ts, "url": url, "status": e.code, "ok": False, "error": str(e)}
    except Exception as e:
        result = {"ts": ts, "url": url, "status": -1, "ok": False, "error": str(e)}

    print(json.dumps(result))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Keep-Alive Pinger")
    parser.add_argument("--url", required=True, help="Streamlit app URL")
    parser.add_argument("--repeat", type=int, default=1, help="Number of pings")
    parser.add_argument("--interval", type=int, default=600, help="Seconds between pings")
    args = parser.parse_args()

    for i in range(args.repeat):
        ping(args.url)
        if i < args.repeat - 1:
            time.sleep(args.interval)
