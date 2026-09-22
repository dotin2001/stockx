"use client";

import type { DependencyList } from "react";
import { useEffect, useState } from "react";

type AsyncState<T> =
  | { status: "idle" | "loading"; data: null; error: null }
  | { status: "success"; data: T; error: null }
  | { status: "error"; data: null; error: Error };

export function useApiResource<T>(loader: () => Promise<T>, deps: DependencyList) {
  const [state, setState] = useState<AsyncState<T>>({ status: "idle", data: null, error: null });

  useEffect(() => {
    let active = true;
    setState({ status: "loading", data: null, error: null });

    loader()
      .then((data) => {
        if (active) {
          setState({ status: "success", data, error: null });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setState({ status: "error", data: null, error: error instanceof Error ? error : new Error("Request failed.") });
        }
      });

    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
