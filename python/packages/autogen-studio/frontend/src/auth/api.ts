import { getServerUrl } from "../components/utils/utils";

export interface User {
  id: string;
  name: string;
  email?: string;
  avatar_url?: string;
  provider?: string;
  roles?: string[];
}

export class AuthAPI {
  private getBaseUrl(): string {
    return getServerUrl();
  }

  private getHeaders(token?: string): HeadersInit {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    return headers;
  }

  async getLoginUrl(): Promise<string> {
    try {
      const response = await fetch(`${this.getBaseUrl()}/auth/login-url`, {
        headers: this.getHeaders(),
      });

      const data = await response.json();
      if (!data.login_url) {
        throw new Error("Failed to get login URL");
      }

      return data.login_url;
    } catch (error) {
      console.error("Error getting login URL:", error);
      throw error;
    }
  }

  async handleCallback(
    code: string,
    state?: string
  ): Promise<{ token: string; user: User }> {
    try {
      const response = await fetch(
        `${this.getBaseUrl()}/auth/callback-handler`,
        {
          method: "POST",
          headers: this.getHeaders(),
          body: JSON.stringify({ code, state }),
        }
      );

      const data = await response.json();
      if (!data.token || !data.user) {
        throw new Error("Authentication failed");
      }

      return data;
    } catch (error) {
      console.error("Error handling auth callback:", error);
      throw error;
    }
  }

  async getCurrentUser(token: string): Promise<User> {
    try {
      const response = await fetch(`${this.getBaseUrl()}/auth/me`, {
        headers: this.getHeaders(token),
      });

      if (response.status === 401) {
        throw new Error("Unauthorized");
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error getting current user:", error);
      throw error;
    }
  }

  async checkAuthType(): Promise<{ type: string }> {
    try {
      const response = await fetch(`${this.getBaseUrl()}/auth/type`, {
        headers: this.getHeaders(),
      });

      const data = await response.json();
      return data;
    } catch (error) {
      console.error("Error checking auth type:", error);
      return { type: "none" }; // Default to no auth
    }
  }
}

export const authAPI = new AuthAPI();
