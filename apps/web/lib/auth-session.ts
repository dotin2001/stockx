import type { AuthResponse } from "@/lib/types";

export type AuthSessionSnapshot = {
  accessToken: string | null;
  generation: number;
};

export type AuthSessionAdapter = {
  snapshot: () => AuthSessionSnapshot;
  refresh: (expectedGeneration: number) => Promise<AuthResponse | null>;
  terminate: (expectedGeneration: number) => void;
};

type CoordinatorDependencies = {
  snapshot: () => AuthSessionSnapshot;
  requestRefresh: () => Promise<AuthResponse>;
  apply: (response: AuthResponse, expectedGeneration: number) => boolean;
  terminate: (expectedGeneration: number) => void;
};

export function createAuthSessionCoordinator(dependencies: CoordinatorDependencies): AuthSessionAdapter {
  let inFlight: { generation: number; promise: Promise<AuthResponse | null> } | null = null;

  return {
    snapshot: dependencies.snapshot,
    refresh(expectedGeneration) {
      if (dependencies.snapshot().generation !== expectedGeneration) return Promise.resolve(null);
      if (inFlight?.generation === expectedGeneration) return inFlight.promise;

      const promise = dependencies.requestRefresh()
        .then((response) => (dependencies.apply(response, expectedGeneration) ? response : null))
        .catch((error: unknown) => {
          dependencies.terminate(expectedGeneration);
          throw error;
        })
        .finally(() => {
          if (inFlight?.promise === promise) inFlight = null;
        });

      inFlight = { generation: expectedGeneration, promise };
      return promise;
    },
    terminate: dependencies.terminate
  };
}
