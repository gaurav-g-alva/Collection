# ⚛️ React CLI Commands Cheat Sheet

## ⚙️ Project Initialization
| Command | Description |
|--------|-------------|
| `npx create-react-app my-app` | Create a new React app using Create React App |
| `yarn create react-app my-app` | Same as above, using Yarn |
| `npm init vite@latest my-app -- --template react` | Create a new React app using Vite |
| `yarn create vite my-app --template react` | Vite setup using Yarn |

## 🚀 Development Server
| Command | Description |
|--------|-------------|
| `npm start` or `yarn start` | Start the development server (CRA) |
| `npm run dev` or `yarn dev` | Start development server (Vite, Next.js) |

## 🔨 Build for Production
| Command | Description |
|--------|-------------|
| `npm run build` or `yarn build` | Create a production build |
| `npm run export` | Export static site (Next.js only) |

## 🧪 Testing
| Command | Description |
|--------|-------------|
| `npm test` or `yarn test` | Run tests using Jest (CRA) |
| `npm run test:watch` | Run tests in watch mode |

## 🧼 Linting & Formatting
| Command | Description |
|--------|-------------|
| `npm run lint` | Run ESLint (must be configured) |
| `npm run format` | Format code using Prettier (must be configured) |

## 📦 Package Management
| Command | Description |
|--------|-------------|
| `npm install package-name` | Install a package |
| `npm install package-name --save-dev` | Install as dev dependency |
| `npm uninstall package-name` | Uninstall a package |
| `npm update` | Update installed packages |
| `npm list` | List installed packages |

## 📁 File Generators (Optional)
| Command | Description |
|--------|-------------|
| `npx plop` | Run component/file generators (if configured) |
| `npx create-next-app my-app` | Create a new Next.js app |

## 📚 package.json Scripts
Run these using `npm run <script>` or `yarn <script>`:
| Script | Description |
|--------|-------------|
| `start` | Start development server |
| `build` | Build the app for production |
| `test` | Run tests |
| `eject` | Eject from CRA (not reversible!) |
