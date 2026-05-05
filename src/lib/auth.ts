import { NextFunction, Request, Response } from "express";
import { ApiError } from "./http.js";
import { createUserScopedClient, supabaseAdmin } from "./supabase.js";

export interface AuthenticatedRequest extends Request {
  auth?: {
    userId: string;
    email: string | null;
    accessToken: string;
  };
}

export async function requireAuth(req: AuthenticatedRequest, _res: Response, next: NextFunction) {
  const header = req.headers.authorization ?? "";
  const accessToken = header.startsWith("Bearer ") ? header.slice("Bearer ".length) : "";
  if (!accessToken) throw new ApiError(401, "Missing bearer token");

  const { data, error } = await supabaseAdmin.auth.getUser(accessToken);
  if (error || !data.user) throw new ApiError(401, "Invalid or expired token");

  req.auth = {
    userId: data.user.id,
    email: data.user.email ?? null,
    accessToken,
  };
  return next();
}

export function getAuth(req: AuthenticatedRequest) {
  if (!req.auth) throw new ApiError(401, "Unauthorized");
  return req.auth;
}

export function getUserClient(req: AuthenticatedRequest) {
  const auth = getAuth(req);
  return createUserScopedClient(auth.accessToken);
}
