---
myst:
  html_meta:
    "description lang=en": |
      FAQ for AutoGen Studio - A low code tool for building and debugging multi-agent systems
---

## Experimental Features

### Authentication (GitHub OAuth)

AutoGen Studio ships with an **experimental** authentication system that lets you run multi-user instances. At the moment, GitHub OAuth is the only provider, but you can extend the base `AuthProvider` class to add others.

Authentication is **off by default**. Enable it by passing an `--auth-config` file (see below) or the corresponding environment variable.

---

#### 1  Create `auth.yaml`

```yaml
type: github

# Generate a strong 32-byte key:
# openssl rand -hex 32
jwt_secret: "YOUR-JWT-SECRET"

token_expiry_minutes: 60       # default = 60

github:
  client_id: "YOUR-CLIENT-ID"
  client_secret: "YOUR-CLIENT-SECRET"
  callback_url: "http://localhost:8081/api/auth/callback"
  scopes: ["user:email"]
```

> [!NOTE]
> * **JWT secret** - keep it out of version control; store and rotate it via your secrets manager.
> * **Callback URL** - must match the value in your GitHub OAuth app settings and be publicly reachable if you're running on a remote host.

For details on generating a client ID/secret, see GitHub's [OAuth guide](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authenticating-to-the-rest-api-with-an-oauth-app).

---

#### 2  Start AutoGen Studio with Auth Enabled

```bash
autogenstudio ui --auth-config /path/to/auth.yaml
```

--or--

```bash
export AUTOGENSTUDIO_AUTH_CONFIG=/path/to/auth.yaml
autogenstudio ui
```

---

#### 3  What Changes When Auth Is On?

| Area                      | Behavior                                                             |
| ------------------------- | -------------------------------------------------------------------- |
| **REST endpoints**        | All require a valid JWT, **except** the auth endpoints themselves.   |
| **WebSocket connections** | Append `?token=<JWT>` to the connection URL.                         |
| **User data**             | Stored in your configured database.                                  |
| **Stability**             | Feature is experimental; expect breaking changes in future releases. |

---
