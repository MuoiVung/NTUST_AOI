# NTUST-AOI-UI — Architecture Reference

> Read this when you need to understand **component structure, WebSocket flow, and data patterns**.
> For what this module does, its interfaces, and how to run it, see [`README.md`](README.md).

---

## 1. Tech Stack

| Component | Library / Tool | Version |
|---|---|---|
| Framework | React | 19.x |
| Build tool | Vite | 6.x |
| Language | TypeScript | ~5.8 |
| Charts | Recharts | 3.x |
| HTTP calls | Native `fetch` (in `services/`) | — |
| Real-time | Native `WebSocket` | — |
| Dev server | `localhost:3001` | — |

---

## 2. Component Tree

```
App.tsx                         # Router + layout wrapper
├── OperatorDashboard.tsx       # Main HMI panel — live run status, barcode input, image stream
│   └── ImageViewer.tsx         # WebSocket subscriber → renders captured images in real time
├── RunList.tsx                 # Paginated history of all inspection runs
├── RunGallery.tsx              # Image grid view for a single run
├── Dashboard.tsx               # Metrics overview (Recharts charts)
├── NewInspection.tsx           # Form to start a new inspection (POST /runs/start)
├── EditRun.tsx                 # Edit and annotate an existing run
└── Settings.tsx                # System configuration UI (GET/PUT /system-configs/)
```

**Shared layers:**
- `types.ts` — TypeScript interfaces: `InspectionRun`, `CapturedImage`, `Order`, `RunStep`, etc.
- `services/` — `fetch` wrapper functions for all API calls (one file per resource)
- `utils/` — Shared utility functions (formatting, date handling, etc.)

---

## 3. WebSocket Subscription Flow

```
ImageViewer.tsx mounts
    │
    ▼
new WebSocket("ws://localhost:8000/ws/ui-updates")
    │
    ▼  [on message]
Parse JSON payload: { type, image_id, run_number, side, ... }
    │
    ▼
Fetch image binary: GET /images/{image_id}/file
    │
    ▼
Render <img> with blob URL
```

**Reconnection:** `ImageViewer.tsx` implements exponential backoff reconnection.
If you refactor this component, preserve that logic. The WebSocket connection
can drop on network hiccups or server restarts.

**Image binary NOT sent over WebSocket.** WS only sends metadata (image_id).
The `<img>` tag fetches the binary separately from `GET /images/proxy/{id}`.

---

## 4. Data Fetching Pattern

All API calls go through `services/` wrappers — never call `fetch` directly
in components. Example pattern:

```typescript
// services/runs.ts
export async function getRuns(params?: RunListParams): Promise<InspectionRun[]> {
  const res = await fetch(`${API_BASE}/runs/?${new URLSearchParams(params)}`);
  if (!res.ok) throw new Error(`GET /runs/ failed: ${res.status}`);
  return res.json();
}
```

Environment variables (set in `.env`):
```
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/ui-updates
```

---

## 5. Key Design Constraints

1. **The UI is stateless.** All data comes from the API or WebSocket. Do not persist
   inspection state in React state across sessions.

2. **WebSocket reconnection is owned by `ImageViewer.tsx`.** Preserve the exponential
   backoff logic if refactoring this component.

3. **Image binary does NOT go through WebSocket.** WS = metadata only; binary
   fetched separately via HTTP.

4. **`OperatorDashboard.tsx` is the largest component (~30KB).** Extract sub-concerns
   into child components rather than adding more logic here.

5. **Typed contracts in `types.ts` are the shared API contract** between frontend and
   backend. When adding a new API field, update `types.ts` first.
