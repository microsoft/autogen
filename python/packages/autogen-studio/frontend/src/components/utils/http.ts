// import { navigate } from "gatsby";
// import { getServerUrl } from "./utils";

// const TOKEN_KEY = "auth_token";

// interface RequestOptions extends RequestInit {
//   requireAuth?: boolean;
// }

// interface HttpResponse<T> {
//   data: T;
//   status: boolean;
//   message?: string;
// }

// class HttpClient {
//   private baseUrl: string;

//   constructor() {
//     this.baseUrl = getServerUrl();
//   }

//   private getToken(): string | null {
//     return localStorage.getItem(TOKEN_KEY);
//   }

//   private getHeaders(options?: RequestOptions): Headers {
//     const headers = new Headers({
//       "Content-Type": "application/json",
//       ...options?.headers,
//     });

//     if (options?.requireAuth !== false) {
//       const token = this.getToken();
//       if (token) {
//         headers.append("Authorization", `Bearer ${token}`);
//       }
//     }

//     return headers;
//   }

//   private handleError(status: number): void {
//     if (status === 401) {
//       // Unauthorized - clear token and redirect to login
//       localStorage.removeItem(TOKEN_KEY);
//       navigate("/login");
//     }
//   }

//   async get<T>(
//     endpoint: string,
//     options?: RequestOptions
//   ): Promise<HttpResponse<T>> {
//     try {
//       const response = await fetch(`${this.baseUrl}${endpoint}`, {
//         method: "GET",
//         headers: this.getHeaders(options),
//         ...options,
//       });

//       if (!response.ok) {
//         this.handleError(response.status);
//         const errorData = await response.json();
//         throw new Error(errorData.message || "Request failed");
//       }

//       const data = await response.json();
//       return data;
//     } catch (error) {
//       console.error(`GET ${endpoint} failed:`, error);
//       throw error;
//     }
//   }

//   async post<T>(
//     endpoint: string,
//     body: any,
//     options?: RequestOptions
//   ): Promise<HttpResponse<T>> {
//     try {
//       const response = await fetch(`${this.baseUrl}${endpoint}`, {
//         method: "POST",
//         headers: this.getHeaders(options),
//         body: JSON.stringify(body),
//         ...options,
//       });

//       if (!response.ok) {
//         this.handleError(response.status);
//         const errorData = await response.json();
//         throw new Error(errorData.message || "Request failed");
//       }

//       const data = await response.json();
//       return data;
//     } catch (error) {
//       console.error(`POST ${endpoint} failed:`, error);
//       throw error;
//     }
//   }

//   async put<T>(
//     endpoint: string,
//     body: any,
//     options?: RequestOptions
//   ): Promise<HttpResponse<T>> {
//     try {
//       const response = await fetch(`${this.baseUrl}${endpoint}`, {
//         method: "PUT",
//         headers: this.getHeaders(options),
//         body: JSON.stringify(body),
//         ...options,
//       });

//       if (!response.ok) {
//         this.handleError(response.status);
//         const errorData = await response.json();
//         throw new Error(errorData.message || "Request failed");
//       }

//       const data = await response.json();
//       return data;
//     } catch (error) {
//       console.error(`PUT ${endpoint} failed:`, error);
//       throw error;
//     }
//   }

//   async delete<T>(
//     endpoint: string,
//     options?: RequestOptions
//   ): Promise<HttpResponse<T>> {
//     try {
//       const response = await fetch(`${this.baseUrl}${endpoint}`, {
//         method: "DELETE",
//         headers: this.getHeaders(options),
//         ...options,
//       });

//       if (!response.ok) {
//         this.handleError(response.status);
//         const errorData = await response.json();
//         throw new Error(errorData.message || "Request failed");
//       }

//       const data = await response.json();
//       return data;
//     } catch (error) {
//       console.error(`DELETE ${endpoint} failed:`, error);
//       throw error;
//     }
//   }
// }

// export const http = new HttpClient();
