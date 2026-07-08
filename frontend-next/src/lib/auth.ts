import Cookies from "js-cookie";

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string;
  role: "admin" | "hr_manager" | "recruiter" | "candidate";
  is_active: boolean;
  is_verified: boolean;
  avatar_url?: string | null;
  organization_id?: string | null;
  created_at: string;
}

export function setTokens(accessToken: string, refreshToken: string) {
  Cookies.set("access_token", accessToken, { expires: 1, sameSite: "strict" });
  Cookies.set("refresh_token", refreshToken, { expires: 7, sameSite: "strict" });
  if (typeof localStorage !== "undefined") {
    localStorage.setItem("access_token", accessToken);
    localStorage.setItem("refresh_token", refreshToken);
  }
}

export function getAccessToken(): string | null {
  return Cookies.get("access_token") || (typeof localStorage !== "undefined" ? localStorage.getItem("access_token") : null);
}

export function getRefreshToken(): string | null {
  return Cookies.get("refresh_token") || (typeof localStorage !== "undefined" ? localStorage.getItem("refresh_token") : null);
}

export function clearTokens() {
  Cookies.remove("access_token");
  Cookies.remove("refresh_token");
  if (typeof localStorage !== "undefined") {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
  }
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

export function setUser(user: User) {
  if (typeof localStorage !== "undefined") {
    localStorage.setItem("user", JSON.stringify(user));
  }
}

export function getStoredUser(): User | null {
  if (typeof localStorage === "undefined") return null;
  try {
    const raw = localStorage.getItem("user");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function getRoleLabel(role: string): string {
  const labels: Record<string, string> = {
    admin: "Administrator",
    hr_manager: "HR Manager",
    recruiter: "Recruiter",
    candidate: "Candidate",
  };
  return labels[role] || role;
}

export function canAccess(userRole: string, requiredRoles: string[]): boolean {
  return requiredRoles.includes(userRole);
}
