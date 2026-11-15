/**
 * A one-shot hint for the next Kirish screen, set just before a sign-out that must lead to a specific sign-in
 * (the password setup's `reauth_required` → "sign in again with a code"). The shell's sign-out reset opens the
 * Kirish tab when one is pending; LoginScreen takes it once.
 */
export type LoginIntent = { mode: 'password' | 'code' | 'reset'; notice?: string };
let pending: LoginIntent | null = null;
export const setLoginIntent = (intent: LoginIntent) => {
  pending = intent;
};
export const hasLoginIntent = () => pending !== null;
export function takeLoginIntent(): LoginIntent | null {
  const p = pending;
  pending = null;
  return p;
}
