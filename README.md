# MarginLab Pricing Lab — Web App

Streamlit front-end for the MarginLab v10 Excel pricing engine.
The Excel stays the canonical calculation model. This app is a thin skin:
**input form → populate Excel → LibreOffice headless recalc → render results.**

---

## Local development

```bash
# 1. Install Python packages
pip install -r requirements.txt

# 2. Run
streamlit run app.py
```

The app opens at http://localhost:8501

**Default consultant password (local):** `marginlab2024`
Change this before deploying by setting the `CONSULTANT_PASSWORD` env var or secret.

---

## Deploy to Streamlit Community Cloud (free, ~5 min)

### Step 1 — Push to GitHub

```bash
# From the marginlab_app/ folder
git init
git add .
git commit -m "MarginLab Pricing Lab v1"

# Create a new repo on github.com (call it marginlab-app or anything)
# Then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

**Important:** Add a `.gitignore` to avoid committing the SQLite DB and temp files:
```
submissions.db
*.xlsx.tmp
__pycache__/
.streamlit/secrets.toml
```

### Step 2 — Connect to Streamlit Community Cloud

1. Go to https://share.streamlit.io and sign in with GitHub
2. Click **New app**
3. Pick your repository and branch (`main`)
4. Set **Main file path** to `app.py`
5. Click **Deploy**

Streamlit Cloud will auto-install everything from `requirements.txt` and `packages.txt`
(including LibreOffice). First deploy takes ~3 minutes.

### Step 3 — Set the consultant password

1. In your deployed app, click the **⋮ menu** (top right) → **Settings**
2. Under **Secrets**, paste:
   ```toml
   CONSULTANT_PASSWORD = "your_strong_password_here"
   ```
3. Click **Save** — the app restarts with the new secret

### Step 4 — Custom subdomain (optional)

In Streamlit Cloud app settings, under **General**, you can set a custom subdomain:
`marginlab.streamlit.app` → enable and type `marginlab` (or whatever's available).

For a fully custom domain (e.g. `app.marginlab.io`):
- Streamlit Community Cloud does not support custom domains natively
- Options: put Cloudflare in front with a CNAME, or upgrade to Streamlit Teams ($)
- For now, the `.streamlit.app` subdomain is fine for demos and client calls

---

## What each file does

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI — input form, results view, admin tab |
| `engine.py` | Excel pipeline — write inputs, recalc, read results |
| `db.py` | SQLite persistence — saves every submission |
| `pdf_report.py` | PDF/HTML report generator |
| `MarginLab_Pricing_Lab_v10.xlsx` | The calculation engine — never edit formulas |
| `requirements.txt` | Python packages |
| `packages.txt` | System packages (LibreOffice etc) for Streamlit Cloud |
| `.streamlit/config.toml` | Theme (brand colors) |
| `.streamlit/secrets.toml.example` | Template for the consultant password |
| `submissions.db` | SQLite database — auto-created on first run |

---

## Updating the Excel model

The app reads from these fixed cell addresses. **You can change any formula inside these
cells freely.** The only breaking change is moving or renaming the cells themselves.

| Sheet | Cells | What the app reads |
|---|---|---|
| SETTINGS | B4:B16 | Currency, round step, guardrails |
| OWNER_INPUTS | B6:G35 | Item inputs |
| COMPETITOR_BENCHMARK | D9:F38 | Competitor prices |
| OWNER_RESULTS | A3 | Banner (data quality warning) |
| OWNER_RESULTS | A5, C5, E5, G5, G7 | Headline metrics |
| OWNER_RESULTS | A11:K40 | Per-item table |
| SENSITIVITY | H40, I40, J40, H44 | Scenario totals |
| QA_CHECKS | B37, B38, B39, C37 | QA summary |

---

## Cost

**$0/month** on Streamlit Community Cloud until you hit ~hundreds of MAU.
At that point the model is generating far more than any hosting cost.

| Component | Cost |
|---|---|
| Streamlit Community Cloud | Free |
| GitHub | Free |
| LibreOffice | Open source |
| SQLite | A file |
| Custom `.streamlit.app` subdomain | Free |
| Custom domain (optional) | ~$12/year |

---

## Troubleshooting

**LibreOffice not found:** Make sure `packages.txt` is in the root of your repo and contains `libreoffice`. Streamlit Cloud installs apt packages from this file automatically.

**"Template not found":** The `MarginLab_Pricing_Lab_v10.xlsx` file must be in the same directory as `app.py` and committed to the GitHub repo.

**Recalc timeout:** Default timeout is 60 seconds. On Streamlit Cloud first run may be slow. If it times out consistently, check the LibreOffice logs in the app's **Manage app** console.

**PDF not generating:** weasyprint requires the pango libraries in `packages.txt`. If PDF still fails, the app falls back to HTML download automatically.

**Submissions not persisting between deploys:** Streamlit Community Cloud has an ephemeral filesystem — the SQLite DB resets on each redeploy. For persistent storage, replace SQLite with a free-tier Supabase (Postgres) or PlanetScale DB. This is a 30-line change in `db.py`.
