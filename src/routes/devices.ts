import { Router } from "express";
import { z } from "zod";
import { env } from "../config/env.js";
import { ApiError, asyncHandler } from "../lib/http.js";

const router = Router();

const connectSchema = z.object({
  address: z.string().optional(),
});

const targetPowerSchema = z.object({
  watts: z.number().int().min(0).max(4000),
});

const targetResistanceSchema = z.object({
  level: z.number().int(),
});

const simulationSchema = z.object({
  gradePct: z.number().default(0),
  windSpeedMs: z.number().default(0),
  crr: z.number().default(0.004),
  cda: z.number().default(0.51),
});

async function engineFetch(path: string, init?: RequestInit) {
  const url = `${env.ENGINE_SERVICE_URL}${path}`;
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      typeof body === "object" && body && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `Engine service error (${response.status})`;
    throw new ApiError(response.status === 404 ? 404 : 502, detail);
  }
  return body;
}

router.get(
  "/health",
  asyncHandler(async (_req, res) => {
    try {
      const data = await engineFetch("/health");
      res.json({ data });
    } catch {
      res.status(503).json({ error: "Engine service unavailable" });
    }
  }),
);

router.get(
  "/state",
  asyncHandler(async (_req, res) => {
    const data = await engineFetch("/state");
    res.json({ data });
  }),
);

router.get(
  "/scan",
  asyncHandler(async (_req, res) => {
    const data = await engineFetch("/scan");
    res.json({ data });
  }),
);

router.post(
  "/connect",
  asyncHandler(async (req, res) => {
    const payload = connectSchema.parse(req.body ?? {});
    const data = await engineFetch("/connect", {
      method: "POST",
      body: JSON.stringify({ address: payload.address }),
    });
    res.json({ data });
  }),
);

router.post(
  "/disconnect",
  asyncHandler(async (_req, res) => {
    const data = await engineFetch("/disconnect", { method: "POST" });
    res.json({ data });
  }),
);

router.post(
  "/control/target-power",
  asyncHandler(async (req, res) => {
    const payload = targetPowerSchema.parse(req.body);
    const data = await engineFetch("/control/target-power", {
      method: "POST",
      body: JSON.stringify({ watts: payload.watts }),
    });
    res.json({ data });
  }),
);

router.post(
  "/control/target-resistance",
  asyncHandler(async (req, res) => {
    const payload = targetResistanceSchema.parse(req.body);
    const data = await engineFetch("/control/target-resistance", {
      method: "POST",
      body: JSON.stringify({ level: payload.level }),
    });
    res.json({ data });
  }),
);

router.post(
  "/control/simulation",
  asyncHandler(async (req, res) => {
    const payload = simulationSchema.parse(req.body);
    const data = await engineFetch("/control/simulation", {
      method: "POST",
      body: JSON.stringify({
        grade_pct: payload.gradePct,
        wind_speed_ms: payload.windSpeedMs,
        crr: payload.crr,
        cda: payload.cda,
      }),
    });
    res.json({ data });
  }),
);

export default router;
