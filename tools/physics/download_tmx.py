"""Download TM2020 maps + replays from trackmania.exchange for physics fitting.

Usage: python download_tmx.py <out-dir> [max_maps=250]
Writes <out-dir>/maps/{MapId}.Map.Gbx, <out-dir>/replays/{MapId}_{ReplayId}.Replay.Gbx,
<out-dir>/index.json. Kacky-tagged maps (TMX tag 23) with replays come first.
Then: dotnet run --project tools/ghost_probe -- <out-dir>/replays <out-dir>/telemetry
"""
import json, os, sys, time, urllib.request

API = "https://trackmania.exchange"
HEADERS = {"User-Agent": "tm2020-claude-tracks research (github.com/SemyonGit)"}
KACKY_TAG = 23


def req(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30)


def search(extra, pages):
    out, after = [], None
    for _ in range(pages):
        r = json.load(req(f"{API}/api/maps?count=100&fields=MapId,MapUid,Name,ReplayCount,Tags{extra}"
                          + (f"&after={after}" if after else "")))
        out += r["Results"]
        if not r.get("More") or not r["Results"]:
            break
        after = r["Results"][-1]["MapId"]
        time.sleep(0.3)
    return [m for m in out if m.get("ReplayCount", 0) > 0]


def main(out, max_maps):
    os.makedirs(f"{out}/maps", exist_ok=True)
    os.makedirs(f"{out}/replays", exist_ok=True)
    maps, seen = [], set()
    for m in search(f"&tag={KACKY_TAG}", 15) + search("", 40):
        if m["MapId"] not in seen:
            m["kacky"] = any(t["TagId"] == KACKY_TAG for t in m.get("Tags", []))
            maps.append(m); seen.add(m["MapId"])
    print("maps with replays:", len(maps))
    n = 0
    for m in maps[:max_maps]:
        try:
            reps = json.load(req(f"{API}/api/replays?mapId={m['MapId']}&count=3&fields=ReplayId"))["Results"]
            mp = f"{out}/maps/{m['MapId']}.Map.Gbx"
            if not os.path.exists(mp):
                open(mp, "wb").write(req(f"{API}/mapgbx/{m['MapId']}").read())
            for rp in reps:
                p = f"{out}/replays/{m['MapId']}_{rp['ReplayId']}.Replay.Gbx"
                if not os.path.exists(p):
                    open(p, "wb").write(req(f"{API}/recordgbx/{rp['ReplayId']}").read()); n += 1
            time.sleep(0.3)
        except Exception as e:
            print("skip", m["MapId"], e)
    json.dump(maps, open(f"{out}/index.json", "w"))
    print("replays downloaded:", n)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 250)
