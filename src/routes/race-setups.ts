import { Router } from "express";
import { z } from "zod";
import { requireAuth, getAuth, getUserClient, type AuthenticatedRequest } from "../lib/auth.js";
import { asyncHandler, ok, ApiError } from "../lib/http.js";

const router = Router();

const setupSchema = z.object({
  riderId: z.string().uuid(),
  bikeMode: z.enum(["Road Bike", "TT Bike", "Triathlon Rig"]),
  mapId: z.string().uuid(),
  raceMode: z.enum(["Endurance", "Time Trial", "Sprint Intervals"]),
  laps: z.number().int().min(1).max(20),
  distanceKm: z.number().positive(),
  climate: z.object({
    temperatureC: z.number(),
    humidity: z.number(),
    windKmh: z.number(),
  }),
  skipDeviceChecks: z.boolean(),
  status: z.enum(["draft", "active", "completed"]).default("draft"),
});

router.use(requireAuth);

router.get(
  "/",
  asyncHandler(async (req: AuthenticatedRequest, res) => {
    const auth = getAuth(req);
    const client = getUserClient(req);
    const { data, error } = await client
      .from("race_setups")
      .select("*")
      .eq("user_id", auth.userId)
      .order("updated_at", { ascending: false });
    if (error) throw new ApiError(400, error.message);
    return ok(res, data ?? []);
  }),
);

router.post(
  "/",
  asyncHandler(async (req: AuthenticatedRequest, res) => {
    const auth = getAuth(req);
    const payload = setupSchema.parse(req.body);
    const client = getUserClient(req);
    const { data, error } = await client
      .from("race_setups")
      .insert({
        user_id: auth.userId,
        rider_id: payload.riderId,
        bike_mode: payload.bikeMode,
        map_id: payload.mapId,
        race_mode: payload.raceMode,
        laps: payload.laps,
        distance_km: payload.distanceKm,
        climate: payload.climate,
        skip_device_checks: payload.skipDeviceChecks,
        status: payload.status,
      })
      .select("*")
      .single();
    if (error) throw new ApiError(400, error.message);
    return ok(res, data);
  }),
);

router.put(
  "/:id",
  asyncHandler(async (req: AuthenticatedRequest, res) => {
    const auth = getAuth(req);
    const id = z.string().uuid().parse(req.params.id);
    const payload = setupSchema.parse(req.body);
    const client = getUserClient(req);
    const { data, error } = await client
      .from("race_setups")
      .update({
        rider_id: payload.riderId,
        bike_mode: payload.bikeMode,
        map_id: payload.mapId,
        race_mode: payload.raceMode,
        laps: payload.laps,
        distance_km: payload.distanceKm,
        climate: payload.climate,
        skip_device_checks: payload.skipDeviceChecks,
        status: payload.status,
        updated_at: new Date().toISOString(),
      })
      .eq("id", id)
      .eq("user_id", auth.userId)
      .select("*")
      .single();
    if (error) throw new ApiError(400, error.message);
    return ok(res, data);
  }),
);

export default router;
