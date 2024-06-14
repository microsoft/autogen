"use client";

import {
  DevtoolsPanel,
  DevtoolsProvider as DevtoolsProviderBase,
} from "@refinedev/devtools";
import React from "react";

export const DevtoolsProvider = (props: React.PropsWithChildren) => {
  return (
    <DevtoolsProviderBase>
      {props.children}
      <DevtoolsPanel />
    </DevtoolsProviderBase>
  );
};
