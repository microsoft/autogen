import { AuthBindings } from "@refinedev/core";
import { cookies } from "next/headers";

export const authProviderServer: Pick<AuthBindings, "check"> = {
  check: async () => {
    const cookieStore = cookies();
    const auth = cookieStore.get("auth");

    if (auth) {
      return {
        authenticated: true,
      };
    }

    return {
      authenticated: false,
      logout: true,
      redirectTo: "/login",
    };
  },
};
