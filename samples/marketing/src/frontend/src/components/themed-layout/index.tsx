"use client";

import { Header } from "@components/header";
import { ThemedLayoutV2 } from "@refinedev/mui";
import React from "react";

export const ThemedLayout = ({ children }: React.PropsWithChildren) => {
  return (
    <ThemedLayoutV2 Header={() => <Header sticky />}>{children}</ThemedLayoutV2>
  );
};
