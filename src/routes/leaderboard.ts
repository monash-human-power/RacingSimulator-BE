import { Router } from "express";
import { z } from "zod";
import { requireAuth } from "../lib/auth.js";
import { asyncHandler, ok, ApiError } from "../lib/http.js";
import { supabaseAnon } from "../lib/supabase.js";

const router = Router();

router.use(requireAuth);

router.get(
  "/",
  asyncHandler(async (req, res) => {
    const mapId = z.string().uuid().optional().parse(req.query.mapId);
    const raceMode = z.enum(["Endurance", "Time Trial", "Sprint Intervals"]).optional().parse(req.query.raceMode);
    const sort = z.enum(["time", "efficiency", "lap"]).default("time").parse(req.query.sort ?? "time");
    const limit = z.coerce.number().int().min(1).max(100).default(50).parse(req.query.limit ?? 50);

    let query = supabaseAnon
      .from("leaderboard_entries")
      .select(
        "id, user_id, session_id, map_id, race_mode, final_time_sec, efficiency, best_lap_sec, avg_power, avg_speed, avg_heart_rate, created_at, maps(name), sessions(riders(first_name, last_name))",
      )
      .limit(limit);

    if (mapId) query = query.eq("map_id", mapId);
    if (raceMode) query = query.eq("race_mode", raceMode);

    if (sort === "efficiency") query = query.order("efficiency", { ascending: false });
    else if (sort === "lap") query = query.order("best_lap_sec", { ascending: true });
    else query = query.order("final_time_sec", { ascending: true });

    const { data, error } = await query;
    if (error) throw new ApiError(400, error.message);
    return ok(res, data ?? []);
  }),
);

export default router;
