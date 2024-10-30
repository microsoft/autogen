"use client";

import { Authenticated } from "@refinedev/core";
import { ErrorComponent } from "@refinedev/mui";
import { Suspense } from "react";

export default function NotFound() {
  return (
    <Suspense>
      <Authenticated key="not-found">
        <ErrorComponent />
      </Authenticated>
    </Suspense>
  );
}
