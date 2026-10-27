"""Download official Kacky maps (kacky.gg) + top ghosts (trackmania.io) for physics fitting.

Usage: python download_kacky.py <out-dir> [ghosts_per_map=5]
Writes <out-dir>/maps/{mapUid}.Map.Gbx, <out-dir>/replays/{mapUid}_{rank}.Ghost.Gbx,
<out-dir>/index.json (event, map number, WR, finishers). Resumable: skips existing files.
Then: dotnet run --project tools/ghost_probe -- <out-dir>/replays <out-dir>/telemetry
"""
import json, os, sys, time, urllib.request

KACKY = "https://api.kacky.gg/v1"
TMIO = "https://trackmania.io"
HEADERS = {"User-Agent": "tm2020-claude-tracks research / github.com/SemyonGit"}
TM2020_EVENT_TYPES = {"KR", "KX"}  # Kacky Reloaded, Kackiest Kacky X (TM2020 editions)
DELAY = 0.6  # s between trackmania.io calls; be polite


def req(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60)


def get(url):
    return json.load(req(url))


def save(url, path):
    if os.path.exists(path):
        return False
    data = req(url).read()
    with open(path + ".part", "wb") as f:
        f.write(data)
    os.replace(path + ".part", path)
    return True


def main(out, per_map):
    os.makedirs(f"{out}/maps", exist_ok=True)
    os.makedirs(f"{out}/replays", exist_ok=True)
    events = [e for e in get(f"{KACKY}/events?limit=500")["data"] if e["eventType"] in TM2020_EVENT_TYPES]
    index = []
    for e in sorted(events, key=lambda e: e["startTime"]):
        maps = get(f"{KACKY}/events/{e['id']}/maps?limit=1000")["data"]
        print(f"{e['eventType']}{e['edition']}: {len(maps)} maps", flush=True)
        for m in maps:
            uid = m["mapUid"]
            entry = {"event": f"{e['eventType']}{e['edition']}", "mapNumber": m["mapNumber"], "mapUid": uid,
                     "authorTime": m.get("authorTime"), "wrTime": m.get("wrTime"),
                     "finishers": m.get("totalFinishers"), "ghosts": []}
            try:
                info = get(f"{TMIO}/api/map/{uid}"); time.sleep(DELAY)
                save(info["fileUrl"], f"{out}/maps/{uid}.Map.Gbx")
                tops = get(f"{TMIO}/api/leaderboard/map/{uid}?offset=0&length={per_map}").get("tops") or []
                time.sleep(DELAY)
                for t in tops[:per_map]:
                    if not t.get("url"):
                        continue
                    p = f"{out}/replays/{uid}_{t['position']}.Ghost.Gbx"
                    if save(TMIO + t["url"], p):
                        time.sleep(DELAY)
                    entry["ghosts"].append({"position": t["position"], "time": t["time"], "file": os.path.basename(p)})
            except Exception as ex:
                print(f"  skip #{m['mapNumber']} {uid}: {ex}", flush=True)
            index.append(entry)
        json.dump(index, open(f"{out}/index.json", "w"), indent=1)
    print("maps:", len(index), "ghosts:", sum(len(i["ghosts"]) for i in index))


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 5)
