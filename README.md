# Nextcloud Photos — TRMNL Plugin

Show photos from your Nextcloud instance on your [TRMNL](https://usetrmnl.com) e-paper display.

Supports sequential, shuffle, random, newest, and oldest selection modes. Optional metadata overlay shows date, location, camera, exposure, and more.

Requests are proxied through `trmnl.bettens.dev` so TRMNL can authenticate with Nextcloud on your behalf. Credentials are never stored — only used to fetch the current image on demand.

---

## Setup

1. Install the plugin from the TRMNL marketplace.
2. Enter your Nextcloud URL, username, and an [app password](https://docs.nextcloud.com/server/latest/user_manual/en/session_management.html#managing-devices) generated in **Settings → Security → App passwords**.
3. Set the folder path (e.g. `/Photos/Wallpapers`) and choose a selection mode.

---

## Advanced: Self-Hosting the Backend

> **For advanced users.** Most users can skip this section — the shared backend at `trmnl.bettens.dev` works out of the box.

If you prefer to run your own backend (for privacy, reliability, or customization), follow these steps.

### Requirements

- Docker and Docker Compose
- A publicly accessible server (TRMNL's servers must be able to reach it)

### 1. Clone and configure

```bash
git clone https://github.com/ExcuseMi/trmnl-nextcloud-photos-plugin.git
cd trmnl-nextcloud-photos-plugin
```

Create a `.env` file:

```env
# Public URL of your backend (used to build image preview URLs returned to TRMNL)
BACKEND_URL=https://your-server.example.com

# Change these in production
POSTGRES_PASSWORD=changeme
REDIS_PASSWORD=changeme
```

All available variables:

| Variable | Default | Description |
|---|---|---|
| `BACKEND_URL` | `http://localhost:8080` | Public base URL of this backend |
| `BACKEND_PORT` | `8474` | Host port the backend listens on |
| `POSTGRES_USER` | `postgres` | PostgreSQL username |
| `POSTGRES_PASSWORD` | `postgres` | PostgreSQL password |
| `POSTGRES_DB` | `postgres` | PostgreSQL database name |
| `REDIS_PASSWORD` | `password` | Redis password |
| `ENABLE_IP_WHITELIST` | `true` | Restrict requests to TRMNL's IP ranges |
| `IP_REFRESH_HOURS` | `24` | How often to refresh TRMNL's IP list |

### 2. Start the stack

```bash
docker compose up -d
```

The backend starts on port `8474` (configurable via `BACKEND_PORT`). It exposes:

- `POST /image` — main endpoint polled by TRMNL
- `GET /image/preview` — proxies the Nextcloud preview image
- `GET /health` — health check

### 3. Expose it publicly

Put the backend behind a reverse proxy (nginx, Caddy, Traefik, etc.) with HTTPS. Example Caddy block:

```
your-server.example.com {
    reverse_proxy localhost:8474
}
```

### 4. Point the plugin at your backend

In the TRMNL plugin settings, set **Custom Backend URL** to your backend's full endpoint:

```
https://your-server.example.com/image
```

Leave the field empty to use the default shared backend.

### IP whitelist

By default the backend only accepts requests from TRMNL's published IP ranges (fetched from `https://trmnl.com/api/ips` and refreshed every 24 hours). Set `ENABLE_IP_WHITELIST=false` to disable — useful during local testing.
