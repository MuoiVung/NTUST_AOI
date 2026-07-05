# NTUST-AOI-UI — Module README

## Responsibility

This module is the **Operator Dashboard (HMI)**. It is a React web application that provides the human-machine interface for factory floor operators. It connects to the FastAPI backend via HTTP and WebSocket.

## Files

| File / Dir | Responsibility |
|---|---|
| `App.tsx` | Main router and layout wrapper |
| `types.ts` | Shared TypeScript interfaces (InspectionRun, CapturedImage, Order, etc.) |
| `components/OperatorDashboard.tsx` | Main HMI panel — largest component (30KB). Shows live run status, barcode input, image stream. |
| `components/ImageViewer.tsx` | WebSocket subscriber. Receives `ui_update` events and renders captured images in real time. |
| `components/RunList.tsx` | Paginated history of all inspection runs |
| `components/RunGallery.tsx` | Image grid view for a single run |
| `components/Dashboard.tsx` | Metrics overview with Recharts charts |
| `components/NewInspection.tsx` | Form to start a new inspection (calls `POST /runs/start`) |
| `components/EditRun.tsx` | Edit and annotate an existing run |
| `components/Settings.tsx` | System configuration UI (calls `/configs/`) |
| `services/` | `fetch` wrapper functions for all API calls |
| `utils/` | Shared utility functions |

## Interfaces

**Inbound (what this module receives):**
- WebSocket messages from `ws://localhost:8000/ws/ui-updates` — JSON payload on each new image
- HTTP responses from `http://localhost:8000` — runs, images, orders, configs

**Outbound (what this module sends):**
- `POST /runs/start` — to queue a new inspection
- `GET /runs/`, `GET /images/`, `GET /orders/` — to read data
- `GET /images/proxy/{id}` — to display image binaries

## Environment Variables

Set in `.env` (copy from `.env.example`):

```
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws/ui-updates
```

## Run (Development)

```bash
cd NTUST-AOI-UI
npm install
npm run dev
# Serves on http://localhost:3001
```

## Build (Production)

```bash
npm run build
# Output in dist/ — to be wrapped by Electron for standalone deployment
```

## Critical Constraints

1. **The UI is stateless.** All data comes from the API or WebSocket. Do not store inspection state in React state across sessions.
2. **WebSocket reconnection is handled in `ImageViewer.tsx`.** If you refactor this component, ensure the reconnection logic (exponential backoff) is preserved.
3. **Image binary is NOT served through the WebSocket.** The WS only sends metadata (image_id). The `<img>` tag fetches the binary from `GET /images/proxy/{id}`.
