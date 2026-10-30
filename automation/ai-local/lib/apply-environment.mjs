import { assertLocal } from "./errors.mjs";

export const TEST_POSTGRES_DATABASE_URL = "TEST_POSTGRES_DATABASE_URL";

const EMPTY_APPLY_TEST_ENVIRONMENT = Object.freeze({});
const POSTGRESQL_SCHEME = /^postgresql(?:\+[a-z0-9][a-z0-9_.-]*)?$/i;

export function resolveApplyTestEnvironment(source = process.env) {
  if (!Object.hasOwn(source, TEST_POSTGRES_DATABASE_URL)) return EMPTY_APPLY_TEST_ENVIRONMENT;

  const value = source[TEST_POSTGRES_DATABASE_URL];
  assertLocal(
    typeof value === "string" && value.length > 0 && value.trim() === value,
    "TEST_POSTGRES_DATABASE_URL",
    `${TEST_POSTGRES_DATABASE_URL} must be a non-empty PostgreSQL SQLAlchemy URL`,
  );

  const scheme = value.match(/^([a-z][a-z0-9+.-]*):\/\//i)?.[1] || "";
  assertLocal(
    POSTGRESQL_SCHEME.test(scheme),
    "TEST_POSTGRES_DATABASE_URL",
    `${TEST_POSTGRES_DATABASE_URL} must use the PostgreSQL dialect`,
  );

  try {
    new URL(value);
  } catch {
    assertLocal(false, "TEST_POSTGRES_DATABASE_URL", `${TEST_POSTGRES_DATABASE_URL} is not a valid SQLAlchemy database URL`);
  }

  return Object.freeze({ [TEST_POSTGRES_DATABASE_URL]: value });
}

export function addApplyTestEnvironment(target, applyTestEnvironment = EMPTY_APPLY_TEST_ENVIRONMENT) {
  const value = applyTestEnvironment?.[TEST_POSTGRES_DATABASE_URL];
  if (typeof value === "string") target[TEST_POSTGRES_DATABASE_URL] = value;
  return target;
}
