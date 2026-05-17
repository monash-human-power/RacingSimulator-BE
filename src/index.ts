import express from "express";
import cors from "cors";
import { env } from "./config/env.js";
import authRoutes from "./routes/auth.js";
import riderRoutes from "./routes/riders.js";
import sessionRoutes from "./routes/sessions.js";
import mapRoutes from "./routes/maps.js";
import leaderboardRoutes from "./routes/leaderboard.js";
import preferencesRoutes from "./routes/preferences.js";
import raceSetupRoutes from "./routes/race-setups.js";
import deviceRoutes from "./routes/devices.js";
import { errorHandler } from "./lib/http.js";

const app = express();

app.use(
  cors({
    origin: env.FRONTEND_URL,
    credentials: false,
  }),
);
app.use(express.json({ limit: "2mb" }));

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

app.use("/api/auth", authRoutes);
app.use("/api/riders", riderRoutes);
app.use("/api/sessions", sessionRoutes);
app.use("/api/maps", mapRoutes);
app.use("/api/leaderboard", leaderboardRoutes);
app.use("/api/preferences", preferencesRoutes);
app.use("/api/race-setups", raceSetupRoutes);
app.use("/api/devices", deviceRoutes);

app.use(errorHandler);

app.listen(env.PORT, () => {
  // eslint-disable-next-line no-console
  console.log(`RacingSimulator BE listening on ${env.PORT}`);
});
