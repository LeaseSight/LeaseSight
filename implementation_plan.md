# LeaseSight – Full-Stack Upgrade Plan
## FastAPI Hardening + Settings Page + Professional SaaS UI

After reviewing the entire codebase I see that a lot of the work is already done — the FastAPI backend in `api/main.py` and the Next.js frontend in `leasesight-ui/` are both live. The remaining gaps are exactly what you asked for. Here's what I'll build.

---

## Current State Assessment

| Area | Status |
|---|---|
| FastAPI endpoints (`/upload`, `/audit`, `/chat`, `/locate`, etc.) | ✅ Exists in `api/main.py` |
| API keys via request headers (not `.env`) | ❌ **Still reads from `.env`** — needs refactoring |
| Settings page (API key storage in `localStorage`) | ❌ **Missing entirely** |
| API service injecting keys from `localStorage` | ❌ `api.ts` doesn't send key headers |
| Dashboard dual-pane layout | ✅ Exists (`LeftPane` + `RightPane`) |
| Visual grounding coordinate math in React | ✅ Already implemented in `RightPane.tsx` |
| Professional SaaS design (branding, nav, etc.) | ⚠️ Functional but needs SaaS polish |

---

## Proposed Changes

### Task 1 — FastAPI: Accept API Keys via Headers

#### [MODIFY] [main.py](file:///c:/Users/zain/OneDrive/Desktop/LeaseSight/api/main.py)

Refactor ALL hardcoded `os.getenv()` client initializations. Instead:
- Add a `Depends()` helper that reads `X-OpenAI-Key`, `X-Pinecone-Key`, `X-Azure-Key`, and `X-Azure-Endpoint` from request headers.
- Pass dynamically-built clients into every endpoint that calls an AI service (`/upload`, `/audit`, `/chat`, `/locate`, `/analytics`, `/query-analytics`).
- Fall back to `.env` values if headers are absent — so the backend still works when run locally without a UI.
- The module-level `oai_client` and `pc` globals will be replaced with per-request client creation inside a `get_clients()` dependency.

Similarly refactor `scripts/full_audit.py`, `scripts/processor.py`, and `scripts/query_engine.py` to **accept client objects as parameters** instead of building them internally from `os.getenv()`.

---

### Task 2 — Next.js: Settings Page + API Service Upgrade

#### [NEW] `leasesight-ui/src/app/settings/page.tsx`

A full Settings page with:
- A card for each API provider: **OpenAI**, **Pinecone**, **Azure Form Recognizer** (key + endpoint).
- `<input type="password">` fields with show/hide toggle.
- Save button that writes to `localStorage` under the keys `ls_openai_key`, `ls_pinecone_key`, `ls_azure_key`, `ls_azure_endpoint`.
- A live "Test Connection" button that calls `/api/health` with the entered keys.
- Status badges (Connected / Error / Untested).
- Premium glassmorphism SaaS design matching the existing theme.

#### [MODIFY] [api.ts](file:///c:/Users/zain/OneDrive/Desktop/LeaseSight/leasesight-ui/src/lib/api.ts)

Add a `getStoredKeys()` helper that reads from `localStorage`. Upgrade `fetchJSON` to automatically inject the 4 key headers (`X-OpenAI-Key`, `X-Pinecone-Key`, `X-Azure-Key`, `X-Azure-Endpoint`) on every request. No component-level changes needed — this is transparent.

#### [MODIFY] [Header.tsx](file:///c:/Users/zain/OneDrive/Desktop/LeaseSight/leasesight-ui/src/components/Header.tsx)

Add:
- A **Settings** navigation link/button that routes to `/settings`.
- A **key status indicator** (shows a warning icon if no keys are saved in `localStorage`).

#### [MODIFY] [globals.css](file:///c:/Users/zain/OneDrive/Desktop/LeaseSight/leasesight-ui/src/app/globals.css)

Add a dark-mode SaaS color palette upgrade. Make the existing light theme more polished: deeper shadows, better typography scale, premium brand gradient for the logo wordmark.

#### [MODIFY] [layout.tsx](file:///c:/Users/zain/OneDrive/Desktop/LeaseSight/leasesight-ui/src/app/layout.tsx)

Add the Inter + JetBrains Mono Google Fonts import for premium typography.

---

### Task 3 — Visual Grounding: Already Working + Document It

The coordinate math in `RightPane.tsx` is already correct. I'll add:

#### [MODIFY] [RightPane.tsx](file:///c:/Users/zain/OneDrive\Desktop/LeaseSight/leasesight-ui/src/components/RightPane.tsx)

- Fix the `max-h-[800px]` constraint that clips tall documents — make it `h-full` so the viewer fills the pane.
- Add page navigation controls (previous/next page) so users can browse beyond page 1.
- Add a page count display and a `numPages` state.
- Render ALL pages (or a virtualized set) rather than only `internalTargetPage`, so context is visible.

---

### Professional SaaS UI Upgrades (across components)

> [!IMPORTANT]
> These are purely visual improvements — no logic changes.

- **Header**: Add gradient logo treatment, settings icon/link, key status badge. Make it feel like a real SaaS topbar.
- **LeftPane**: Upgrade the empty state with an animated icon. Add subtle section dividers.  
- **globals.css**: Add premium SaaS design tokens (brand gradient, better shadows, card surfaces).
- **Settings Page**: Full-page form with branded hero, card groups per provider, animated transitions.

---

## Architecture: How Keys Flow End-to-End

```
User fills in Settings Page → localStorage
        ↓
api.ts getStoredKeys() reads localStorage
        ↓
Every fetch() call injects headers:
  X-OpenAI-Key, X-Pinecone-Key, X-Azure-Key, X-Azure-Endpoint
        ↓
FastAPI get_clients() Depends reads headers
  → Falls back to .env if header is missing
        ↓
Per-request OpenAI / Pinecone / Azure clients
```

---

## Visual Grounding — How the Coordinate Math Works

For your reference (answers Task 3):

The Azure Form Recognizer returns coordinates in **inches** (floating point). The PDF page is a standard US Letter size (8.5 × 11 inches). The React formula in `RightPane.tsx` is:

```js
const PAGE_WIDTH_INCHES  = 8.5;
const PAGE_HEIGHT_INCHES = 11.0;

const pxX = (ann.x / PAGE_WIDTH_INCHES)  * containerWidth;
const pxH = (ann.height / PAGE_HEIGHT_INCHES) * (containerWidth * (PAGE_HEIGHT_INCHES / PAGE_WIDTH_INCHES));
// … etc.
```

This is **already correct**. The 72 DPI reference in the original Python code was a Streamlit artifact — since we emit raw Azure inch-values from the API (DPI = 1.0 in `main.py`), the React math above maps inches directly to pixels at whatever the container's rendered width is.

---

## Open Questions

> [!IMPORTANT]
> **Do you want the backend to REQUIRE headers (reject requests without keys), or should it gracefully fall back to `.env` values?**
> My plan is to use a soft fallback (use header if present, else use `.env`). This keeps local development easy.

> [!IMPORTANT]
> **Multi-page rendering**: Currently `RightPane` renders only the page containing the highlight. Do you want the viewer to render ALL pages (scroll through the whole document), or keep the single-page approach with prev/next buttons?
> My plan is to add prev/next navigation AND render the entire document as a scrollable list.

> [!NOTE]
> The `scripts/full_audit.py`, `scripts/processor.py`, and `scripts/query_engine.py` each instantiate their own OpenAI/Pinecone clients at module level. I will refactor them to accept client objects as parameters. This is a non-breaking internal refactor.

---

## Verification Plan

### Automated
1. Start FastAPI: `uvicorn api.main:app --reload`  
2. Start Next.js: `npm run dev` in `leasesight-ui/`
3. Open Settings page → enter keys → click Save → badge turns green
4. Open Dashboard → select a document → Run Audit → verify results appear
5. Click a finding's locate button → red highlight appears on PDF at correct position

### Manual
- Confirm the Settings page is accessible via the header nav link
- Confirm that clearing keys from Settings causes the health check to fail gracefully
- Confirm the PDF viewer can scroll and navigate pages

