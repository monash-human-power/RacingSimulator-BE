import { Router } from "express";
import { z } from "zod";
import { requireAuth, getAuth, getUserClient, type AuthenticatedRequest } from "../lib/auth.js";
import { asyncHandler, ok, ApiError } from "../lib/http.js";

const router = Router();

const lifecycleSchema = z.object({
  status: z.enum(["draft", "active", "completed"]),
});

const startSchema = z.object({
  raceSetupId: z.string().uuid().optional(),
  riderId: z.string().uuid(),
  mapId: z.string().uuid(),
  raceMode: z.enum(["Endurance", "Time Trial", "Sprint Intervals"]),
  bikeMode: z.enum(["Road Bike", "TT Bike", "Triathlon Rig"]),
  laps: z.number().int().min(1).max(20),
  distanceKm: z.number().positive(),
  climate: z.object({
    temperatureC: z.number(),
    humidity: z.number(),
    windKmh: z.number(),
  }),
  skipDeviceChecks: z.boolean(),
});

const completeSchema = z.object({
  finalTimeSec: z.number().int().positive(),
  avgPower: z.number(),
  avgSpeed: z.number(),
  avgHeartRate: z.number(),
  efficiency: z.number(),
  lapTimesSec: z.array(z.number().int().positive()),
  metricsTimeline: z.array(
    z.object({
      t: z.number(),
      speed: z.number(),
      power: z.number(),
      cadence: z.number(),
      heartRate: z.number(),
    }),
  ),
  analysisSummary: z.object({
    peakOutputNote: z.string(),
    dropZoneNote: z.string(),
    keyMomentNote: z.string(),
    insight: z.string(),
    actualVsTarget: z.object({
      powerTarget: z.number(),
      speedTarget: z.number(),
      hrCap: z.number(),
    }),
  }),
});

router.use(requireAuth);

router.get(
  "/",
  asyncHandler(async (req: AuthenticatedRequest, res) => {
    const auth = getAuth(req);
    const limit = z.coerce.number().int().min(1).max(100).default(50).parse(req.query.limit ?? 50);
    const client = getUserClient(req);
    const { data, error } = await client
      .from("sessions")
      .select(
        "id, rider_id, map_id, race_setup_id, race_mode, bike_mode, laps, distance_km, status, final_time_sec, avg_power, avg_speed, avg_heart_rate, efficiency, started_at, ended_at, created_at, riders(first_name,last_name), maps(name)",
      )
      .eq("user_id", auth.userId)
      .order("created_at", { ascending: false })
      .limit(limit);
    if (error) throw new ApiError(400, error.message);
    return ok(res, data ?? []);
  }),
);

router.get(
  "/:id",
  asyncHandler(async (req: AuthenticatedRequest, res) => {
    const auth = getAuth(req);
    const id = z.string().uuid().parse(req.params.id);
    const client = getUserClient(req);
    const { data: session, error } = await client
      .from("sessions")
      .select("*")
      .eq("id", id)
      .eq("user_id", auth.userId)
      .single();
    if (error) throw new ApiError(404, error.message);

    const [laps, metrics, analysis] = await Promise.all([
      client
        .from("laps")
        .select("lap_number, lap_time_sec")
        .eq("session_id", id)
        .eq("user_id", auth.userId)
        .order("lap_number", { ascending: true }),
      client
        .from("session_metrics")
        .select("t, speed, power, cadence, heart_rate")
        .eq("session_id", id)
        .eq("user_id", auth.userId)
        .order("t", { ascending: true }),
      client
        .from("analysis_summaries")
        .select("peak_output_note, drop_zone_note, key_moment_note, insight, actual_vs_target")
        .eq("session_id", id)
        .eq("user_id", auth.userId)
        .maybeSingle(),
    ]);

    if (laps.error) throw new ApiError(400, laps.error.message);
    if (metrics.error) throw new ApiError(400, metrics.error.message);
    if (analysis.error) throw new ApiError(400, analysis.error.message);

    return ok(res, {
      session,
      laps: laps.data ?? [],
      metricsTimeline: metrics.data ?? [],
      analysis: analysis.data ?? null,
    });
  }),
);

router.post(
  "/start",
  asyncHandler(async (req: AuthenticatedRequest, res) => {
    const auth = getAuth(req);
    const payload = startSchema.parse(req.body);
    const client = getUserClient(req);

    let raceSetupId = payload.raceSetupId;
    if (!raceSetupId) {
      const { data: setup, error: setupError } = await client
        .from("race_setups")
        .insert({
          user_id: auth.userId,
          rider_id: payload.riderId,
          map_id: payload.mapId,
          race_mode: payload.raceMode,
          bike_mode: payload.bikeMode,
          laps: payload.laps,
          distance_km: payload.distanceKm,
          climate: payload.climate,
          skip_device_checks: payload.skipDeviceChecks,
          status: "active",
        })
        .select("id")
        .single();
      if (setupError) throw new ApiError(400, setupError.message);
      raceSetupId = setup.id;
    }

    const { data, error } = await client
      .from("sessions")
      .insert({
        user_id: auth.userId,
        rider_id: payload.riderId,
        map_id: payload.mapId,
        race_setup_id: raceSetupId,
        race_mode: payload.raceMode,
        bike_mode: payload.bikeMode,
        laps: payload.laps,
        distance_km: payload.distanceKm,
        status: "active",
        started_at: new Date().toISOString(),
      })
      .select("*")
      .single();
    if (error) throw new ApiError(400, error.message);

    return ok(res, data);
  }),
);

router.patch(
  "/:id/lifecycle",
  asyncHandler(async (req: AuthenticatedRequest, res) => {
    const auth = getAuth(req);
    const id = z.string().uuid().parse(req.params.id);
    const payload = lifecycleSchema.parse(req.body);
    const client = getUserClient(req);
    const { data, error } = await client
      .from("sessions")
      .update({
        status: payload.status,
        ended_at: payload.status === "completed" ? new Date().toISOString() : null,
      })
      .eq("id", id)
      .eq("user_id", auth.userId)
      .select("*")
      .single();
    if (error) throw new ApiError(400, error.message);
    return ok(res, data);
  }),
);

router.post(
  "/:id/complete",
  asyncHandler(async (req: AuthenticatedRequest, res) => {
    const auth = getAuth(req);
    const id = z.string().uuid().parse(req.params.id);
    const payload = completeSchema.parse(req.body);
    const client = getUserClient(req);

    const { data: session, error: sessionError } = await client
      .from("sessions")
      .update({
        status: "completed",
        ended_at: new Date().toISOString(),
        final_time_sec: payload.finalTimeSec,
        avg_power: payload.avgPower,
        avg_speed: payload.avgSpeed,
        avg_heart_rate: payload.avgHeartRate,
        efficiency: payload.efficiency,
      })
      .eq("id", id)
      .eq("user_id", auth.userId)
      .select("*")
      .single();
    if (sessionError) throw new ApiError(400, sessionError.message);

    const { error: deleteLapsError } = await client.from("laps").delete().eq("session_id", id).eq("user_id", auth.userId);
    if (deleteLapsError) throw new ApiError(400, deleteLapsError.message);
    const { error: deleteMetricsError } = await client
      .from("session_metrics")
      .delete()
      .eq("session_id", id)
      .eq("user_id", auth.userId);
    if (deleteMetricsError) throw new ApiError(400, deleteMetricsError.message);

    if (payload.lapTimesSec.length) {
      const { error: lapsError } = await client.from("laps").insert(
        payload.lapTimesSec.map((lapTimeSec, idx) => ({
          session_id: id,
          user_id: auth.userId,
          lap_number: idx + 1,
          lap_time_sec: lapTimeSec,
        })),
      );
      if (lapsError) throw new ApiError(400, lapsError.message);
    }

    if (payload.metricsTimeline.length) {
      const { error: metricsError } = await client.from("session_metrics").insert(
        payload.metricsTimeline.map((metric) => ({
          session_id: id,
          user_id: auth.userId,
          t: metric.t,
          speed: metric.speed,
          power: metric.power,
          cadence: metric.cadence,
          heart_rate: metric.heartRate,
        })),
      );
      if (metricsError) throw new ApiError(400, metricsError.message);
    }

    const { error: analysisError } = await client.from("analysis_summaries").upsert(
      {
        session_id: id,
        user_id: auth.userId,
        peak_output_note: payload.analysisSummary.peakOutputNote,
        drop_zone_note: payload.analysisSummary.dropZoneNote,
        key_moment_note: payload.analysisSummary.keyMomentNote,
        insight: payload.analysisSummary.insight,
        actual_vs_target: payload.analysisSummary.actualVsTarget,
      },
      { onConflict: "session_id" },
    );
    if (analysisError) throw new ApiError(400, analysisError.message);

    const bestLap = Math.min(...payload.lapTimesSec);
    const { error: leaderboardError } = await client.from("leaderboard_entries").insert({
      user_id: auth.userId,
      session_id: id,
      map_id: session.map_id,
      race_mode: session.race_mode,
      final_time_sec: payload.finalTimeSec,
      efficiency: payload.efficiency,
      best_lap_sec: Number.isFinite(bestLap) ? bestLap : payload.finalTimeSec,
      avg_power: payload.avgPower,
      avg_speed: payload.avgSpeed,
      avg_heart_rate: payload.avgHeartRate,
    });
    if (leaderboardError) throw new ApiError(400, leaderboardError.message);

    const { error: setupError } = await client
      .from("race_setups")
      .update({ status: "completed", updated_at: new Date().toISOString() })
      .eq("id", session.race_setup_id)
      .eq("user_id", auth.userId);
    if (setupError) throw new ApiError(400, setupError.message);

    return ok(res, { success: true, sessionId: id });
  }),
);

export default router;
