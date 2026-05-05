import { Router } from "express";
import { z } from "zod";
import { requireAuth, getAuth, getUserClient, type AuthenticatedRequest } from "../lib/auth.js";
import { asyncHandler, ok, ApiError } from "../lib/http.js";

const router = Router();

const preferencesSchema = z.object({
  units: z.enum(["Metric", "Imperial"]),
  showMapOverlay: z.boolean(),
  showPerformanceDelta: z.boolean(),
  defaultRaceMode: z.enum(["Endurance", "Time Trial", "Sprint Intervals"]),
});

router.use(requireAuth);

router.get(
  "/",
  asyncHandler(async (req: AuthenticatedRequest, res) => {
    const auth = getAuth(req);
    const client = getUserClient(req);
    const { data, error } = await client
      .from("preferences")
      .select("user_id, units, show_map_overlay, show_performance_delta, default_race_mode, updated_at")
      .eq("user_id", auth.userId)
      .maybeSingle();
    if (error) throw new ApiError(400, error.message);
    return ok(res, data);
  }),
);

router.put(
  "/",
  asyncHandler(async (req: AuthenticatedRequest, res) => {
    const auth = getAuth(req);
    const payload = preferencesSchema.parse(req.body);
    const client = getUserClient(req);
    const { data, error } = await client
      .from("preferences")
      .upsert(
        {
          user_id: auth.userId,
          units: payload.units,
          show_map_overlay: payload.showMapOverlay,
          show_performance_delta: payload.showPerformanceDelta,
          default_race_mode: payload.defaultRaceMode,
          updated_at: new Date().toISOString(),
        },
        { onConflict: "user_id" },
      )
      .select("user_id, units, show_map_overlay, show_performance_delta, default_race_mode, updated_at")
      .single();
    if (error) throw new ApiError(400, error.message);
    return ok(res, data);
  }),
);

export default router;
