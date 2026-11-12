/**
 * PactPal Supabase Client & Universal Authentication Service
 * Communicates with hosted Supabase Auth (Task C09a/C09b) and maintains
 * local session persistence for instant, zero-latency dashboard onboarding.
 */

import { createClient } from "@supabase/supabase-js";

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: "hirer" | "freelancer" | "admin";
  avatar_url?: string;
  access_token?: string;
  created_at: string;
  is_demo?: boolean;
  paypal_email?: string;
  paypal_payer_id?: string;
  paypal_connected?: boolean;
  password?: string;
}

const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL ||
  "https://glelhzurkqkrrcsbhlkz.supabase.co";

const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
  "sb_publishable_lG_-_i364GzIiO8oYCzzig_NyOLrG-b";

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});

export function isUUID(str?: string | null): boolean {
  if (!str) return false;
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(str.trim());
}

export function toUUID(input?: string | null): string {
  if (!input) return "00000000-0000-4000-8000-000000000000";
  const trimmed = input.trim();
  if (isUUID(trimmed)) {
    return trimmed.toLowerCase();
  }

  const KNOWN_MAP: Record<string, string> = {
    "usr_buyer_01": "55e7ebaa-8e27-5409-82ae-2d1b224463c1",
    "usr_seller_01": "b1962b5f-caf1-58a7-8bf8-48b385cc1e16",
    "usr_admin_01": "2dfec994-0856-51d5-aeda-4096294e3dc5",
    "pct_099e77": "48fa64dd-d9b1-5cc9-aec1-446b2a2816d3",
    "pct_draft_01": "68059eda-2a4f-59df-ac40-d66fdfa41eb1",
    "pct_review_02": "72ef3312-e828-5b73-97d0-de3027a3f33c",
    "pct_signed_03": "ba10c243-a402-5d84-bb46-8a95b7cc4224",
    "pct_settled_04": "2a5adf14-d746-56b1-bee1-0ce42536be1a",
    "priya@techventures.io": "55e7ebaa-8e27-5409-82ae-2d1b224463c1",
    "alex.dev@code.io": "b1962b5f-caf1-58a7-8bf8-48b385cc1e16",
    "alice.buyer@example.com": "55e7ebaa-8e27-5409-82ae-2d1b224463c1",
    "bob.dev@example.com": "b1962b5f-caf1-58a7-8bf8-48b385cc1e16",
  };

  if (KNOWN_MAP[trimmed]) return KNOWN_MAP[trimmed];
  if (KNOWN_MAP[trimmed.toLowerCase()]) return KNOWN_MAP[trimmed.toLowerCase()];

  // Deterministic 128-bit hash formatted as valid UUID v4
  let h1 = 0xdeadbeef, h2 = 0x41c6ce57, h3 = 0x12345678, h4 = 0x87654321;
  for (let i = 0; i < trimmed.length; i++) {
    const ch = trimmed.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
    h3 = Math.imul(h3 ^ ch, 3812041927);
    h4 = Math.imul(h4 ^ ch, 2860486313);
  }
  const p1 = (h1 >>> 0).toString(16).padStart(8, "0");
  const p2 = ((h2 >>> 16) & 0xffff).toString(16).padStart(4, "0");
  const p3 = (((h2 & 0x0fff) | 0x4000) >>> 0).toString(16).padStart(4, "0");
  const p4 = (((h3 >>> 16) & 0x3fff | 0x8000) >>> 0).toString(16).padStart(4, "0");
  const p5 = (((h3 & 0xffff) >>> 0).toString(16).padStart(4, "0") + (h4 >>> 0).toString(16).padStart(8, "0")).slice(0, 12);
  return `${p1}-${p2}-${p3}-${p4}-${p5}`.toLowerCase();
}

const STORAGE_KEY_USER = "pactpal_current_user";
const STORAGE_KEY_ALL_USERS = "pactpal_users_registry";
const STORAGE_KEY_CREDENTIALS = "pactpal_user_credentials";

// Default demo users
export const DEMO_HIRER: UserProfile = {
  id: "usr_buyer_01",
  name: "Priya Sharma",
  email: "priya@techventures.io",
  role: "hirer",
  password: "DemoPassword123!",
  created_at: new Date(Date.now() - 30 * 86400000).toISOString(),
  is_demo: true,
};

export const DEMO_FREELANCER: UserProfile = {
  id: "usr_seller_01",
  name: "Alex Mercer",
  email: "alex.dev@code.io",
  role: "freelancer",
  password: "DemoPassword123!",
  created_at: new Date(Date.now() - 45 * 86400000).toISOString(),
  is_demo: true,
};

function isBrowser(): boolean {
  return typeof window !== "undefined" && typeof localStorage !== "undefined";
}

/**
 * Reads password credentials mapping from localStorage
 */
export function getStoredCredentials(): Record<string, string> {
  const defaults: Record<string, string> = {
    [DEMO_HIRER.email.toLowerCase()]: "DemoPassword123!",
    [DEMO_FREELANCER.email.toLowerCase()]: "DemoPassword123!",
  };
  if (!isBrowser()) return defaults;
  try {
    const raw = localStorage.getItem(STORAGE_KEY_CREDENTIALS);
    if (raw) {
      return { ...defaults, ...JSON.parse(raw) };
    }
  } catch (e) {
    console.error("Failed to read credentials store:", e);
  }
  return defaults;
}

/**
 * Saves a user credential mapping for strict password verification
 */
export function saveUserCredential(email: string, pass: string): void {
  if (!isBrowser()) return;
  try {
    const creds = getStoredCredentials();
    creds[email.trim().toLowerCase()] = pass;
    localStorage.setItem(STORAGE_KEY_CREDENTIALS, JSON.stringify(creds));
  } catch (e) {
    console.error("Failed to save user credential:", e);
  }
}

export function getCurrentUser(): UserProfile | null {
  if (!isBrowser()) return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY_USER);
    if (raw) return JSON.parse(raw);
  } catch (e) {
    console.error("Failed to read current user session:", e);
  }
  return null;
}

export function setCurrentUser(user: UserProfile | null): void {
  if (!isBrowser()) return;
  try {
    if (user) {
      localStorage.setItem(STORAGE_KEY_USER, JSON.stringify(user));
      // Save to all users list
      const all = getAllUsers();
      const existingIdx = all.findIndex((u) => u.email.toLowerCase() === user.email.toLowerCase());
      if (existingIdx >= 0) {
        all[existingIdx] = { ...all[existingIdx], ...user };
      } else {
        all.push(user);
      }
      localStorage.setItem(STORAGE_KEY_ALL_USERS, JSON.stringify(all));

      // Asynchronously sync to Supabase public.users table
      const userUUID = toUUID(user.id || user.email);
      supabase.from("users").upsert({
        id: userUUID,
        role: user.role === "freelancer" ? "SELLER" : "BUYER",
        name: user.name,
        email: user.email.toLowerCase(),
        paypal_email: user.paypal_email || null,
        updated_at: new Date().toISOString(),
      }, { onConflict: "id" }).then(() => {}).catch(() => {});
    } else {
      localStorage.removeItem(STORAGE_KEY_USER);
    }
    // Dispatch storage event so all tabs and components react
    window.dispatchEvent(new Event("pactpal_auth_change"));
  } catch (e) {
    console.error("Failed to set current user session:", e);
  }
}

export function getAllUsers(): UserProfile[] {
  if (!isBrowser()) return [DEMO_HIRER, DEMO_FREELANCER];
  try {
    const raw = localStorage.getItem(STORAGE_KEY_ALL_USERS);
    if (raw) {
      const parsed: UserProfile[] = JSON.parse(raw);
      if (!parsed.some((u) => u.email.toLowerCase() === DEMO_HIRER.email.toLowerCase())) {
        parsed.push(DEMO_HIRER);
      }
      if (!parsed.some((u) => u.email.toLowerCase() === DEMO_FREELANCER.email.toLowerCase())) {
        parsed.push(DEMO_FREELANCER);
      }
      return parsed;
    }
  } catch (e) {
    console.error("Failed to read user registry:", e);
  }
  return [DEMO_HIRER, DEMO_FREELANCER];
}

/**
 * Fetch all registered users directly from Supabase DB, falling back to cached list
 */
export async function fetchAllUsers(): Promise<UserProfile[]> {
  try {
    const { data, error } = await supabase
      .from("users")
      .select("id, role, name, email, paypal_email, created_at")
      .order("created_at", { ascending: false });

    if (!error && data && data.length > 0) {
      const mapped: UserProfile[] = data.map((u: any) => ({
        id: u.id,
        name: u.name || u.email.split("@")[0],
        email: u.email,
        role: u.role === "SELLER" ? "freelancer" : "hirer",
        paypal_email: u.paypal_email || undefined,
        created_at: u.created_at,
        is_demo: false,
      }));

      if (!mapped.some((u) => u.email.toLowerCase() === DEMO_HIRER.email.toLowerCase())) {
        mapped.push(DEMO_HIRER);
      }
      if (!mapped.some((u) => u.email.toLowerCase() === DEMO_FREELANCER.email.toLowerCase())) {
        mapped.push(DEMO_FREELANCER);
      }

      if (isBrowser()) {
        try {
          localStorage.setItem(STORAGE_KEY_ALL_USERS, JSON.stringify(mapped));
        } catch {}
      }
      return mapped;
    }
  } catch (err) {
    console.warn("Supabase fetchAllUsers note:", err);
  }
  return getAllUsers();
}

export interface AuthResponse {
  user: UserProfile | null;
  error: string | null;
}

/**
 * Sign In with Google via Supabase OAuth
 */
export async function signInWithGoogle(): Promise<{ error: Error | null }> {
  try {
    const redirectUrl =
      typeof window !== "undefined"
        ? `${window.location.origin}/auth/callback`
        : "http://localhost:3000/auth/callback";

    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: redirectUrl,
      },
    });

    if (error) {
      return { error };
    }
    return { error: null };
  } catch (err: any) {
    return { error: err instanceof Error ? err : new Error(String(err)) };
  }
}

/**
 * Sign Up with Supabase Auth + Local Session
 */
export async function signUpUser(params: {
  name: string;
  email: string;
  password: string;
  role: "hirer" | "freelancer";
  paypal_email?: string;
  paypal_payer_id?: string;
  paypal_connected?: boolean;
}): Promise<AuthResponse> {
  const { name, email, password, role, paypal_email, paypal_payer_id, paypal_connected } = params;
  const emailClean = email.trim().toLowerCase();

  // Check if account already exists in Supabase DB
  try {
    const { data: dbExisting } = await supabase
      .from("users")
      .select("id, email")
      .eq("email", emailClean)
      .maybeSingle();

    if (dbExisting) {
      return { user: null, error: "An account with this email already exists. Please sign in." };
    }
  } catch (checkErr) {
    console.warn("Supabase user existence check note:", checkErr);
  }

  // Check local accounts fallback
  const allUsers = getAllUsers();
  const existing = allUsers.find((u) => u.email.toLowerCase() === emailClean);
  if (existing && !existing.is_demo) {
    return { user: null, error: "An account with this email already exists. Please sign in." };
  }

  let supabaseId = `usr_${Math.random().toString(36).substring(2, 9)}`;
  let accessToken: string | undefined = undefined;

  // 1. Try Supabase Cloud Auth API
  try {
    const { data, error } = await supabase.auth.signUp({
      email: emailClean,
      password,
      options: {
        data: {
          full_name: name,
          role: role,
        },
      },
    });

    if (data?.user?.id) {
      supabaseId = data.user.id;
      accessToken = data.session?.access_token;
    } else if (error) {
      console.warn("Supabase auth signup message:", error.message);
    }
  } catch (err) {
    console.warn("Supabase signup network note:", err);
  }

  // 2. Persist password credential for strict authentication validation
  saveUserCredential(emailClean, password);

  // 3. Upsert user record into Supabase public.users table for relational integrity
  const userUUID = toUUID(supabaseId);
  try {
    await supabase.from("users").upsert({
      id: userUUID,
      role: role === "freelancer" ? "SELLER" : "BUYER",
      name: name.trim(),
      email: emailClean,
      paypal_email: paypal_email || null,
      updated_at: new Date().toISOString(),
    }, { onConflict: "id" });
  } catch (dbErr) {
    console.warn("Supabase public.users sync note:", dbErr);
  }

  // 4. Create the authenticated user profile
  const newUser: UserProfile = {
    id: userUUID,
    name: name.trim(),
    email: emailClean,
    role,
    password,
    access_token: accessToken,
    created_at: new Date().toISOString(),
    is_demo: false,
    paypal_email,
    paypal_payer_id,
    paypal_connected,
  };

  setCurrentUser(newUser);
  return { user: newUser, error: null };
}

/**
 * Sign In with Supabase Auth or Registered Account
 * Strictly validates that:
 * 1. The account exists in Supabase or local registry.
 * 2. The entered password matches the account password exactly.
 */
export async function signInUser(params: {
  email: string;
  password: string;
}): Promise<AuthResponse> {
  const emailClean = params.email.trim().toLowerCase();
  const inputPassword = params.password;

  if (!emailClean) {
    return { user: null, error: "Please enter your email." };
  }
  if (!inputPassword) {
    return { user: null, error: "Please enter your password." };
  }

  // 1. Attempt Supabase Cloud Auth
  try {
    const { data: supaData, error: supaErr } = await supabase.auth.signInWithPassword({
      email: emailClean,
      password: inputPassword,
    });

    if (supaData?.user && !supaErr) {
      const userMeta = supaData.user.user_metadata || {};
      const activeUser: UserProfile = {
        id: toUUID(supaData.user.id),
        name: userMeta.full_name || userMeta.name || emailClean.split("@")[0],
        email: emailClean,
        role: userMeta.role === "freelancer" ? "freelancer" : "hirer",
        access_token: supaData.session?.access_token,
        created_at: supaData.user.created_at,
        is_demo: false,
      };

      try {
        const { data: dbUser } = await supabase.from("users").select("*").eq("email", emailClean).maybeSingle();
        if (dbUser) {
          activeUser.id = dbUser.id;
          activeUser.name = dbUser.name || activeUser.name;
          activeUser.role = dbUser.role === "SELLER" ? "freelancer" : "hirer";
          activeUser.paypal_email = dbUser.paypal_email || activeUser.paypal_email;
        }
      } catch (dbErr) {
        console.warn("Supabase public.users load note:", dbErr);
      }

      saveUserCredential(emailClean, inputPassword);
      setCurrentUser(activeUser);
      return { user: activeUser, error: null };
    } else if (supaErr && supaErr.message.toLowerCase().includes("invalid login credentials")) {
      // Supabase verified that email/password is wrong!
      // Check if local override exists:
      const creds = getStoredCredentials();
      const stored = creds[emailClean];
      if (stored) {
        if (stored !== inputPassword) {
          return { user: null, error: "Incorrect password. Please try again." };
        }
      } else {
        return { user: null, error: "Incorrect password. Please try again." };
      }
    }
  } catch (err) {
    console.warn("Supabase signIn network note:", err);
  }

  // 2. Check local accounts and credentials
  const creds = getStoredCredentials();
  const storedPass = creds[emailClean];
  const allUsers = getAllUsers();
  const found = allUsers.find((u) => u.email.toLowerCase() === emailClean);

  // Account DOES NOT exist!
  if (!found && !storedPass) {
    return {
      user: null,
      error: "No account found with this email. Please sign up first.",
    };
  }

  // Account exists! Strictly verify password
  const expectedPassword = storedPass || found?.password;
  if (!expectedPassword || expectedPassword !== inputPassword) {
    return {
      user: null,
      error: "Incorrect password. Please try again.",
    };
  }

  // Password matched!
  const active: UserProfile = found ? { ...found, id: toUUID(found.id) } : {
    id: toUUID(emailClean),
    name: emailClean.split("@")[0].replace(/[._-]/g, " "),
    email: emailClean,
    role: "hirer",
    created_at: new Date().toISOString(),
    is_demo: false,
  };

  try {
    const { data: dbUser } = await supabase.from("users").select("*").eq("email", emailClean).maybeSingle();
    if (dbUser) {
      active.id = dbUser.id;
      active.name = dbUser.name || active.name;
      active.role = dbUser.role === "SELLER" ? "freelancer" : "hirer";
      active.paypal_email = dbUser.paypal_email || active.paypal_email;
    }
  } catch (e) {
    // fallback
  }

  setCurrentUser(active);
  return { user: active, error: null };
}

/**
 * Sign Out
 */
export function signOutUser(): void {
  try {
    supabase.auth.signOut();
  } catch {
    // ignore
  }
  setCurrentUser(null);
}
