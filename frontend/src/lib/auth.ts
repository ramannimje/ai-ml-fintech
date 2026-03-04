export function resolveAuthCallbackUrl(envCallback?: string): string {
  const origin = window.location.origin;
  if (!envCallback) {
    return origin;
  }

  try {
    const envUrl = new URL(envCallback);
    const originUrl = new URL(origin);
    // Avoid localhost/127.0.0.1 mismatch by preferring runtime origin.
    if (envUrl.host !== originUrl.host) {
      return origin;
    }
    return envUrl.toString().replace(/\/$/, '');
  } catch {
    return origin;
  }
}

