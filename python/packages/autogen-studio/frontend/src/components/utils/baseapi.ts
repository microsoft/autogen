import { getServerUrl } from "./utils";

// baseApi.ts
export abstract class BaseAPI {
  protected getBaseUrl(): string {
    return getServerUrl();
  }

  protected getHeaders(): HeadersInit {
    // Get auth token from localStorage
    const token = localStorage.getItem("auth_token");

    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    // Add authorization header if token exists
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    return headers;
  }

  // Other common methods
}
