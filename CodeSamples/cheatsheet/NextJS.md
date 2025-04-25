# ⚛️ Next.js CLI Commands Cheat Sheet

## ⚙️ Project Initialization
| Command | Description |
|--------|-------------|
| `npx create-next-app@latest my-app` | Create a new Next.js project using the latest version |
| `yarn create next-app my-app` | Same as above using Yarn |
| `pnpm create next-app my-app` | Same using pnpm |

## 🚀 Development
| Command | Description |
|--------|-------------|
| `npm run dev` or `yarn dev` | Start development server at http://localhost:3000 |
| `npm run start` or `yarn start` | Start production server (after building) |
| `next dev` | Core dev command (used behind the scenes) |

## 🔨 Building & Exporting
| Command | Description |
|--------|-------------|
| `npm run build` or `yarn build` | Create an optimized production build |
| `next build` | Same as above (raw Next.js command) |
| `npm run export` or `next export` | Export app as static HTML (for static sites) |

## 📦 Custom Server (Optional)
| Command | Description |
|--------|-------------|
| `node server.js` | Run a custom Express/Node.js server with Next.js (if configured) |

## 🧪 Linting, Formatting, and Testing
| Command | Description |
|--------|-------------|
| `next lint` or `npm run lint` | Run ESLint on your Next.js project |
| `npm run format` | Run Prettier to format code (if configured) |
| `npm run test` | Run tests (if you’ve set up a test framework like Jest) |

## 📁 Routing & Pages (File-Based)
> No CLI commands — Next.js uses file-based routing:
- `pages/index.js` → `/`
- `pages/about.js` → `/about`
- `pages/[user].js` → dynamic route like `/john`
- `pages/[[...slug]].js` → catch-all routes

## 💼 Environment & Config
| File | Description |
|------|-------------|
| `.env.local` | Local environment variables (default) |
| `.env.production` | Used during production build |
| `.env.development` | Used during development |
| `next.config.js` | Next.js config file for custom settings (e.g., Webpack, redirects) |

## 🌍 Deployment
| Command | Description |
|--------|-------------|
| `vercel` | Deploy the app using Vercel CLI |
| `npm run build && npm start` | Deploy manually after building |

