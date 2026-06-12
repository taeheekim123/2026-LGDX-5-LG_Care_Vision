import { getUserProfile as getMockUserProfile } from "../data/mockUser";
import type { UserProfile } from "../types/user";

export async function getUserProfile(): Promise<UserProfile> {
  // TODO: Replace with GET /api/users/me when backend is ready.
  return getMockUserProfile();
}

