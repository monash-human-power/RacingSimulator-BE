import { Router } from "express";
import { asyncHandler, ok, ApiError } from "../lib/http.js";
import { supabaseAnon } from "../lib/supabase.js";

const router = Router();

router.get(
  "/",
  asyncHandler(async (_req, res) => {
    const { data, error } = await supabaseAnon
      .from("maps")
      .select("id, name, length_km, terrain, difficulty, elevation_gain_m, default_laps")
      .eq("is_active", true)
      .order("name", { ascending: true });
    if (error) throw new ApiError(400, error.message);
    return ok(res, data ?? []);
  }),
);

export default router;
