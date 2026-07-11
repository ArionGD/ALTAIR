# ALTAIR Dashboard (Astro Frontend)

> 🚧 **Under development — coming soon.** This is not the recommended way to
> use ALTAIR locally right now. For quick local testing, run just the FastAPI
> backend (`python main.py`) and open `http://127.0.0.1:8001/dashboard` — see
> the **project root [README.md](../README.md)** for details and current
> project status. This Astro app is scaffolded and functional, but it's a
> future replacement for that backend-served dashboard, not the current path.

The intended frontend for the ALTAIR fragility engine, eventually. It's a
single dashboard page (`src/pages/index.astro`) that calls the FastAPI backend
(`../main.py`) over plain `fetch()` and renders the strike list and top
targets.

## Structure

```
src/
├── lib/api.ts        # typed fetch client for the FastAPI backend
├── styles/global.css # dashboard styling
└── pages/index.astro # the dashboard page (markup + client-side script)
```

## Commands

| Command         | Action                                                    |
| :--------------- | :--------------------------------------------------------- |
| `npm install`     | Install dependencies                                       |
| `npm run dev`     | Start the dev server at `localhost:4321`                    |
| `npm run build`   | Build the static site to `./dist/` (this is what you'd deploy to Netlify) |
| `npm run preview` | Preview the production build locally                        |
| `npx astro check` | Type-check the project                                      |

## Configuration

Copy `.env.example` to `.env` and set `PUBLIC_API_BASE` if the backend isn't
running at the default `http://127.0.0.1:8001`.
