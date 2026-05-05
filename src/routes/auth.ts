import { Router } from "express";
import { z } from "zod";
import { asyncHandler, ok, ApiError } from "../lib/http.js";
import { requireAuth, getAuth, getUserClient, type AuthenticatedRequest } from "../lib/auth.js";
import { createUserScopedClient, supabaseAnon } from "../lib/supabase.js";

const router = Router();

router.post(
  "/sign-up",
  asyncHandler(async (req, res) => {
    const body = z
      .object({
        email: z.string().email(),
        password: z.string().min(8),
        displayName: z.string().min(1).max(120).optional(),
      })
      .parse(req.body);

    const { data, error } = await supabaseAnon.auth.signUp({
      email: body.email,
      password: body.password,
      options: {
        data: {
          display_name: body.displayName ?? "Rider",
        },
      },
    });
    if (error) throw new ApiError(400, error.message);

    return ok(res, {
      user: data.user,
      session: data.session,
    });
  }),
);

router.post(
  "/sign-in",
  asyncHandler(async (req, res) => {
    const body = z.object({ email: z.string().email(), password: z.string().min(8) }).parse(req.body);
    const { data, error } = await supabaseAnon.auth.signInWithPassword(body);
    if (error) throw new ApiError(401, error.message);
    return ok(res, data);
  }),
);

router.post(
  "/refresh",
  asyncHandler(async (req, res) => {
    const body = z.object({ refreshToken: z.string().min(1) }).parse(req.body);
    const { data, error } = await supabaseAnon.auth.refreshSession({
      refresh_token: body.refreshToken,
    });
    if (error || !data.session) throw new ApiError(401, error?.message ?? "Failed to refresh session");
    return ok(res, data);
  }),
);

router.post(
  "/sign-out",
  asyncHandler(async (req, res) => {
    const body = z.object({ accessToken: z.string().optional() }).parse(req.body ?? {});
    if (!body.accessToken) return ok(res, { success: true });
    const scoped = createUserScopedClient(body.accessToken);
    await scoped.auth.signOut();
    return ok(res, { success: true });
  }),
);

router.post(
  "/reset-password",
  asyncHandler(async (req, res) => {
    const body = z.object({ email: z.string().email(), redirectTo: z.string().url().optional() }).parse(req.body);
    const { error } = await supabaseAnon.auth.resetPasswordForEmail(body.email, {
      redirectTo: body.redirectTo,
    });
    if (error) throw new ApiError(400, error.message);
    return ok(res, { success: true });
  }),
);

router.post(
  "/update-password",
  requireAuth,
  asyncHandler(async (req: AuthenticatedRequest, res) => {
    const body = z.object({ newPassword: z.string().min(8) }).parse(req.body);
    const client = getUserClient(req);
    const { error } = await client.auth.updateUser({ password: body.newPassword });
    if (error) throw new ApiError(400, error.message);
    return ok(res, { success: true });
  }),
);

router.get(
  "/me",
  requireAuth,
  asyncHandler(async (req: AuthenticatedRequest, res) => {
    const auth = getAuth(req);
    const client = getUserClient(req);
    const { data: profile, error } = await client
      .from("profiles")
      .select("user_id, display_name, created_at, updated_at")
      .eq("user_id", auth.userId)
      .maybeSingle();
    if (error) throw new ApiError(400, error.message);
    return ok(res, {
      user: { id: auth.userId, email: auth.email },
      profile,
    });
  }),
);

router.patch(
  "/profile",
  requireAuth,
  asyncHandler(async (req: AuthenticatedRequest, res) => {
    const auth = getAuth(req);
    const body = z.object({ displayName: z.string().min(1).max(120) }).parse(req.body);
    const client = getUserClient(req);
    const { data, error } = await client
      .from("profiles")
      .upsert(
        {
          user_id: auth.userId,
          display_name: body.displayName,
          updated_at: new Date().toISOString(),
        },
        { onConflict: "user_id" },
      )
      .select("user_id, display_name, created_at, updated_at")
      .single();
    if (error) throw new ApiError(400, error.message);
    return ok(res, data);
  }),
);

export default router;
