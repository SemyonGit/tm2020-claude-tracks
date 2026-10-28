"""Download a corpus of regular TM2020 maps from trackmania.exchange (no replays).

Used to learn road-block geometry (#14, #15): Kacky maps barely use road curves/chicanes.
Usage: python download_tmx_maps.py <out-dir> [count=1500]
Skips Kacky-tagged maps (TMX tag 23). Resumable.
"""
import json, os, sys, time, urllib.request

API = "https://trackmania.exchange"
HEADERS = {"User-Agent": "tm2020-claude-tracks research (github.com/SemyonGit)"}


def req(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60)


def main(out, count):
    os.makedirs(out, exist_ok=True)
    after, got = None, len([f for f in os.listdir(out) if f.endswith(".Map.Gbx")])
    while got < count:
        r = json.load(req(f"{API}/api/maps?count=100&fields=MapId,Tags"
                          + (f"&after={after}" if after else "")))
        if not r["Results"]:
            break
        for m in r["Results"]:
            if got >= count or any(t["TagId"] == 23 for t in m.get("Tags", [])):
                continue
            p = f"{out}/{m['MapId']}.Map.Gbx"
            if os.path.exists(p):
                continue
            try:
                data = req(f"{API}/mapgbx/{m['MapId']}").read()
                open(p, "wb").write(data); got += 1
            except Exception as e:
                print("skip", m["MapId"], e, flush=True)
            time.sleep(0.25)
        after = r["Results"][-1]["MapId"]
        print("maps:", got, flush=True)
        if not r.get("More"):
            break


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 1500)
