using GBX.NET;
using GBX.NET.Engines.Game;
using GBX.NET.Engines.Scene;
using GBX.NET.LZO;
using GBX.NET.ZLib;

Gbx.LZO = new Lzo();
Gbx.ZLib = new ZLib();
foreach (var path in args)
{
    Console.WriteLine($"== {Path.GetFileName(path)}");
    var node = Gbx.ParseNode(path);
    var ghosts = node switch
    {
        CGameCtnGhost g => new[] { g },
        CGameCtnReplayRecord r => r.GetGhosts().ToArray(),
        _ => []
    };
    Console.WriteLine($"type={node?.GetType().Name} ghosts={ghosts.Length}");
    foreach (var g in ghosts)
    {
        Console.WriteLine($"ghost: login={g.GhostLogin} time={g.RaceTime} map={g.Validate_ChallengeUid} rec={g.RecordData is not null}");
        if (g.RecordData is null) continue;
        foreach (var e in g.RecordData.EntList)
        {
            var vis = e.Samples.OfType<CSceneVehicleVis.EntRecordDelta>().ToList();
            Console.WriteLine($" ent type={e.Type} samples={e.Samples.Count} vehicleVis={vis.Count}");
            if (vis.Count == 0) continue;
            Console.WriteLine($" dt first: {(vis[1].Time - vis[0].Time).TotalMilliseconds} ms");
            Console.WriteLine("  t_ms,x,y,z,vx,vy,vz,speed_kmh,steer,gas,brake,groundmode");
            foreach (var s in vis)
                Console.WriteLine($"  {s.Time.TotalMilliseconds},{s.Position.X:F2},{s.Position.Y:F2},{s.Position.Z:F2},{s.Velocity.X:F2},{s.Velocity.Y:F2},{s.Velocity.Z:F2},{s.Speed:F1},{s.Steer:F2},{s.Gas:F2},{s.Brake:F2},{((GBX.NET.Engines.Scene.CSceneVehicleVis.IEntRecordDeltaRawData)s).GroundMode}");
        }
    }
}
