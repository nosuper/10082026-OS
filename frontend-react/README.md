# Welcome to your Lovable project

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Open your project in the [Lovable editor](https://lovable.dev) and keep building.

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: connect the project to GitHub and every change made in Lovable is committed straight to your repository.
- **Full ownership**: this code is yours. Push to your repository and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm - [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```

## How it is served

This is a static SPA. `npm run build` writes the bundle to
`auraos/public/aura-next/` and copies the HTML shell to
`auraos/www/aura-next.html`, injecting the `{{ csrf_token }}` Jinja tag.
Frappe then serves the app at `/aura-next` (see `website_route_rules` in
`auraos/hooks.py` and the page context in `auraos/www/aura_next.py`).

Because it is same-origin with Frappe, the session cookie and CSRF token
already in use keep working: no CORS, no token auth, no Node runtime. There is
no SSR and no server function - the router basepath is `/aura-next` so deep
links survive a reload.

`npm run dev` proxies `/api`, `/login`, `/assets`, `/files` and `/private` to a
bench on `http://127.0.0.1:8000`.

## Built with

- Vite
- TanStack Router
- TypeScript
- React
- Tailwind CSS
