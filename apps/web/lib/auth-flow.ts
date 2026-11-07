export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 128;
export const DEFAULT_SUCCESS_COOLDOWN_SECONDS = 30;

export function isValidEmail(value: string) {
  const normalized = value.trim();
  return normalized.length >= 3
    && normalized.length <= 320
    && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized);
}

export function passwordValidationMessage(value: string) {
  if (value.length < PASSWORD_MIN_LENGTH) return `Password must be at least ${PASSWORD_MIN_LENGTH} characters.`;
  if (value.length > PASSWORD_MAX_LENGTH) return `Password must be no more than ${PASSWORD_MAX_LENGTH} characters.`;
  return null;
}
