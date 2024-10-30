import { DevtoolsProvider } from "@providers/devtools";
import { Refine } from "@refinedev/core";
import { RefineKbar, RefineKbarProvider } from "@refinedev/kbar";
import { RefineSnackbarProvider, notificationProvider } from "@refinedev/mui";
import routerProvider from "@refinedev/nextjs-router";
import { Metadata } from "next";
import { cookies } from "next/headers";
import React, { Suspense } from "react";

 export const metadata: Metadata = {
  title: "AgNext Marketing Sample",
  description: "AgNext Marketing Sample",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {

  return (
    <html lang="en">
      <body>
        <Suspense>
          <RefineKbarProvider>
              <RefineSnackbarProvider>
                <DevtoolsProvider>
                  <Refine
                    routerProvider={routerProvider}
                    notificationProvider={notificationProvider}
                    resources={[
                      {
                        name: "marketing-app",
                        list: "/marketing",
                      }
                    ]}
                    options={{
                      syncWithLocation: true,
                      warnWhenUnsavedChanges: true,
                      useNewQueryKeys: true,
                      projectId: "Z0Y3hf-6BZFyJ-VWX5Qq",
                    }}
                  >
                    {children}
                    <RefineKbar />
                  </Refine>
                </DevtoolsProvider>
              </RefineSnackbarProvider>
          </RefineKbarProvider>
        </Suspense>
      </body>
    </html>
  );
}
