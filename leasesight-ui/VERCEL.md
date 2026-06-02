# Deploy LeaseSight UI on Vercel

## 1. Project root directory

In Vercel → **Project Settings → General → Root Directory**, set:

```
leasesight-ui
```

## 2. Environment variables (required)

Vercel does **not** use your `.env.local` file. Add these in **Settings → Environment Variables**:

| Name | Value | Environments |
|------|--------|----------------|
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | `pk_live_...` (from Clerk → API Keys → Production) | Production, Preview |
| `NEXT_PUBLIC_API_URL` | `https://api.leasesights.tech` | Production, Preview |

Optional (only if you add Next.js API routes later):

| `CLERK_SECRET_KEY` | `sk_live_...` | Production |

## 3. Clerk domain (required for login)

In [Clerk Dashboard](https://dashboard.clerk.com) → your app → **Domains**:

- Add your Vercel URL, e.g. `https://your-project.vercel.app`
- Or connect custom domain `www.leasesights.tech` on Vercel (recommended for `pk_live_` keys)

Production keys (`pk_live_`) only work on domains allowed in Clerk (e.g. `leasesights.tech`).

## 4. Redeploy

After saving environment variables: **Deployments → … → Redeploy** (must rebuild so `NEXT_PUBLIC_*` is baked into the static export).

## Local vs production keys

| Where | Clerk keys |
|-------|------------|
| `leasesight-ui/.env.local` | `pk_test_` / `sk_test_` |
| Vercel env vars | `pk_live_` / `sk_live_` |
| Azure `.env.production` | `pk_live_` / `sk_live_` |
