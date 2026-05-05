import { Router } from "express";
import { z } from "zod";
import { requireAuth, getAuth, getUserClient, type AuthenticatedRequest } from "../lib/auth.js";
import { ApiError, asyncHandler, ok } from "../lib/http.js";

const router = Router();

const riderSchema = z.object({
  firstName: z.string().min(1).max(120),
  lastName: z.string().min(1).max(120),
  weightKg: z.number().min(35).max(130),
  experience: z.enum(["Beginner", "Intermediate", "Advanced", "Pro"]),
  notes: z.string().max(1000).default(""),
});

router.use(requireAuth);

router.get(
  "/",
  asyncHandler(async (req: AuthenticatedRequest, res) => {
    const auth = getAuth(req);
    const client = getUserClient(req);
    const { data, error } = await client
      .from("riders")
      .select("id, first_name, last_name, weight_kg, experience, notes, created_at")
      .eq("user_id", auth.userId)
      .order("created_at", { ascending: false });
    if (error) throw new ApiError(400, error.message);
    return ok(res, data ?? []);
  }),
);

router.post(
  "/",
  asyncHandler(async (req: AuthenticatedRequest, res) => {
    const auth = getAuth(req);
    const payload = riderSchema.parse(req.body);
    const client = getUserClient(req);
    const { data, error } = await client
      .from("riders")
      .insert({
        user_id: auth.userId,
        first_name: payload.firstName,
        last_name: payload.lastName,
        weight_kg: payload.weightKg,
        experience: payload.experience,
        notes: payload.notes,
      })
      .select("id, first_name, last_name, weight_kg, experience, notes, created_at")
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
    const payload = riderSchema.parse(req.body);
    const client = getUserClient(req);
    const { data, error } = await client
      .from("riders")
      .update({
        first_name: payload.firstName,
        last_name: payload.lastName,
        weight_kg: payload.weightKg,
        experience: payload.experience,
        notes: payload.notes,
        updated_at: new Date().toISOString(),
      })
      .eq("id", id)
      .eq("user_id", auth.userId)
      .select("id, first_name, last_name, weight_kg, experience, notes, created_at")
      .single();
    if (error) throw new ApiError(400, error.message);
    return ok(res, data);
  }),
);

router.delete(
  "/:id",
  asyncHandler(async (req: AuthenticatedRequest, res) => {
    const auth = getAuth(req);
    const id = z.string().uuid().parse(req.params.id);
    const client = getUserClient(req);
    const { error } = await client.from("riders").delete().eq("id", id).eq("user_id", auth.userId);
    if (error) throw new ApiError(400, error.message);
    return ok(res, { success: true });
  }),
);

export default router;
