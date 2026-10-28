// Export TM2020 ghost/replay telemetry to CSV.
// Usage: dotnet run -- <file-or-dir> [<out-dir>]
//   file  → prints CSV to stdout
//   dir   → one CSV per *.Replay.Gbx / *.Ghost.Gbx into out-dir (default: ./telemetry)
// Map mode: dotnet run -- map <map-dir> <out-dir>
//   → one CSV per *.Map.Gbx: blocks (grid + free) and items, positions in world metres
using GBX.NET;
using GBX.NET.Engines.Game;
using GBX.NET.Engines.Scene;
using GBX.NET.LZO;
using GBX.NET.ZLib;
using System.Globalization;

Gbx.LZO = new Lzo();
Gbx.ZLib = new ZLib();
CultureInfo.DefaultThreadCurrentCulture = CultureInfo.InvariantCulture;
CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;

const string Header =
    "t_ms,x,y,z,qx,qy,qz,qw,vx,vy,vz,speed_kmh,steer,gas,brake,gear,rpm," +
    "ground,fl_mat,fr_mat,rl_mat,rr_mat,fl_damp,fr_damp,rl_damp,rr_damp,turbo,sim_coef,wetness,gmode";

if (args.Length == 0) { Console.Error.WriteLine("usage: <file-or-dir> [out-dir] | map <map-dir> <out-dir>"); return 1; }

if (args[0] == "map") return ExportMaps(args[1], args[2]);

if (File.Exists(args[0]))
{
    foreach (var (_, rows) in Extract(args[0])) { Console.WriteLine(Header); rows.ForEach(Console.WriteLine); }
    return 0;
}

var outDir = args.Length > 1 ? args[1] : "telemetry";
Directory.CreateDirectory(outDir);
int ok = 0, fail = 0;
var meta = new List<string> { "file,ghost,map_uid,login,race_ms,samples,vehicle" };
foreach (var path in Directory.EnumerateFiles(args[0]).Where(p =>
             p.EndsWith(".Replay.Gbx", StringComparison.OrdinalIgnoreCase) ||
             p.EndsWith(".Ghost.Gbx", StringComparison.OrdinalIgnoreCase)))
{
    try
    {
        var i = 0;
        foreach (var (g, rows) in Extract(path))
        {
            var name = $"{Path.GetFileName(path).Split('.')[0]}_{i++}.csv";
            File.WriteAllLines(Path.Combine(outDir, name), rows.Prepend(Header));
            meta.Add($"{name},{i - 1},{g.Validate_ChallengeUid},{g.GhostLogin},{g.RaceTime?.TotalMilliseconds},{rows.Count},{g.PlayerModel?.Id}");
        }
        ok++;
    }
    catch (Exception e) { fail++; Console.Error.WriteLine($"FAIL {Path.GetFileName(path)}: {e.GetType().Name}: {e.Message}"); }
}
File.WriteAllLines(Path.Combine(outDir, "_index.csv"), meta);
Console.WriteLine($"parsed {ok}, failed {fail}, ghosts {meta.Count - 1}");
return 0;

static IEnumerable<(CGameCtnGhost, List<string>)> Extract(string path)
{
    var node = Gbx.ParseNode(path);
    var ghosts = node switch
    {
        CGameCtnGhost g => [g],
        CGameCtnReplayRecord r => r.GetGhosts().ToArray(),
        _ => Array.Empty<CGameCtnGhost>()
    };
    foreach (var g in ghosts)
    {
        if (g.RecordData is null) continue;
        var samples = g.RecordData.EntList
            .Select(e => e.Samples.OfType<CSceneVehicleVis.EntRecordDelta>().ToList())
            .OrderByDescending(s => s.Count)
            .FirstOrDefault();
        if (samples is null || samples.Count == 0) continue;
        yield return (g, samples.Select(Row).ToList());
    }
}

static string Row(CSceneVehicleVis.EntRecordDelta s)
{
    var raw = (CSceneVehicleVis.IEntRecordDeltaRawData)s;
    return string.Join(",",
        s.Time.TotalMilliseconds,
        s.Position.X, s.Position.Y, s.Position.Z,
        s.Rotation.X, s.Rotation.Y, s.Rotation.Z, s.Rotation.W,
        s.Velocity.X, s.Velocity.Y, s.Velocity.Z,
        s.Speed, s.Steer, s.Gas, s.Brake, s.Gear, s.RPM,
        s.IsGroundContact ? 1 : 0,
        (int)s.FLGroundContactMaterial, (int)s.FRGroundContactMaterial,
        (int)s.RLGroundContactMaterial, (int)s.RRGroundContactMaterial,
        s.FLDampenLen, s.FRDampenLen, s.RLDampenLen, s.RRDampenLen,
        raw.IsTurbo, raw.SimulationTimeCoef, s.WetnessValue, raw.GroundMode);
}

// Grid cell → world metres: 32 m horizontally, 8 m vertically, y shifted by 8 cells
// (measured: ghost spawn = start-block corner + (16, -62, 16) on 5/5 grid starts).
// Block origin is the cell corner. Free blocks/items are already in world metres.
static int ExportMaps(string dir, string outDir)
{
    Directory.CreateDirectory(outDir);
    int ok = 0, fail = 0;
    foreach (var path in Directory.EnumerateFiles(dir, "*.Map.Gbx"))
    {
        try
        {
            var map = Gbx.ParseNode<CGameCtnChallenge>(path);
            var rows = new List<string> { "kind,name,x,y,z,gx,gy,gz,dir,yaw,pitch,roll,variant,ground" };
            foreach (var b in map.GetBlocks())
            {
                if (b.IsFree && b.AbsolutePositionInMap is { } p)
                {
                    var r = b.YawPitchRoll ?? default;
                    rows.Add($"free,{Q(b.Name)},{p.X},{p.Y},{p.Z},,,,,{r.X},{r.Y},{r.Z},{b.Variant},0");
                }
                else
                {
                    var c = b.Coord;
                    rows.Add($"block,{Q(b.Name)},{c.X * 32},{(c.Y - 8) * 8},{c.Z * 32},{c.X},{c.Y},{c.Z},{b.Direction},,,,{b.Variant},{(b.IsGround ? 1 : 0)}");
                }
            }
            foreach (var it in map.GetAnchoredObjects())
            {
                var p = it.AbsolutePositionInMap; var r = it.PitchYawRoll;
                rows.Add($"item,{Q(it.ItemModel.Id)},{p.X},{p.Y},{p.Z},,,,,{r.Y},{r.X},{r.Z},,");
            }
            var uid = map.MapUid ?? Path.GetFileName(path).Split('.')[0];
            File.WriteAllLines(Path.Combine(outDir, $"{uid}.blocks.csv"), rows);
            ok++;
        }
        catch (Exception e) { fail++; Console.Error.WriteLine($"FAIL {Path.GetFileName(path)}: {e.GetType().Name}: {e.Message}"); }
    }
    Console.WriteLine($"maps parsed {ok}, failed {fail}");
    return 0;
}

static string Q(string? s) => s is null ? "" : s.Contains(',') || s.Contains('"') ? $"\"{s.Replace("\"", "\"\"")}\"" : s;
