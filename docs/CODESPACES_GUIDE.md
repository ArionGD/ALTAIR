# Running ALTAIR in GitHub Codespaces

This is a cloud alternative to running `python main.py` on your laptop — you get
a full VS Code (in the browser), a terminal, and a real HTTPS URL you can open
like `http://127.0.0.1:8001`, all without installing anything locally.

Works for any repo you own, not just ALTAIR — the steps are the same.

---

## 1. Create a Codespace (one-time per branch)

1. Open the repo on GitHub: `https://github.com/ArionGD/ALTAIR`
2. Click the green **`Code`** button → **`Codespaces`** tab → **`Create codespace on <branch>`**
   (pick the branch you want, e.g. `claude/paper-trading-platform-wqsy3j`, or `main`).
3. Wait ~1–2 minutes while it builds the container. It opens **VS Code in your
   browser** with the repo already checked out — same file tree, same git
   history, same branch.

## 2. Run the backend

In the Codespace's built-in terminal:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

- A toast notification appears: **"Your application running on port 8001 is
  available."** → click **Open in Browser**.
- Or manually: bottom panel → **`Ports`** tab → click the 🌐 globe icon next
  to port `8001`.
- Either way you get a URL like `https://<name>-8001.app.github.dev` — it
  behaves exactly like `127.0.0.1:8001` locally. Open `/dashboard` there for
  the analysis UI.

### If you're working on the Astro frontend

```bash
cd astro
npm install
npm run dev
```

Same port-forward flow, just on whatever port Astro prints (default `4321`).

## 3. Test / verify

- Hit the API directly from the same forwarded URL, e.g.
  `https://<name>-8001.app.github.dev/api/v1/health`.
- `data/` is gitignored, so a fresh Codespace has no CSVs — click **Run Full
  Audit** on the dashboard, or `POST /api/v1/audit`, to populate data (live
  scrape, takes a few minutes, same as running locally).

## 4. Commit and push

Same as any git workflow — use the terminal or VS Code's **Source Control**
panel. You're on the same branch as your local clone, so `git push` behaves
identically.

## 5. Shutting down

- Just close the tab — Codespaces auto-suspends the container after ~30 min
  of inactivity, so it doesn't burn your free hours while idle.
- When you're fully done with a branch, go to `github.com/codespaces` and
  delete the Codespace to free it up.

**Free tier:** 60 core-hours/month on a personal GitHub account — no GCP
project or billing setup required for this part. (Save the GCP credits for
actually hosting a deployed trial, e.g. on Cloud Run, not for the IDE itself.)
