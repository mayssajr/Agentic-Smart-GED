## ged-smart-assistant-ui

#### Description

`ged-smart-assistant-ui` is the standalone frontend for the GED Smart Assistant experience. It provides the landing page and chat interface for interacting with the assistant

#### Architecture Role

This repository will communicate with the orchestration backend and related realtime services.

#### Features

- Vue-based landing page and chat route
- PrimeVue-based UI components and styling
- TailwindCSS integration
- Static chat flow for interface prototyping
- Axios service layer and WebSocket client scaffolding for backend integration

#### Tech Stack

- Vue 3
- JavaScript
- Vite
- Vue Router
- PrimeVue
- PrimeIcons
- TailwindCSS
- Axios

#### Installation

Prerequisites:

- Node.js 18+ and npm

Install dependencies:

```bash
npm install
```

#### Usage

Run the development server:

```bash
npm run dev
```

Build for production:

```bash
npm run build
```

Preview the production build:

```bash
npm run preview
```

#### Project Structure

- `src/views`: page views such as home and chat
- `src/components`: reusable UI pieces like message bubbles and chat input
- `src/services`: integration helpers
- `src/data`: static data used for UI prototyping
- `src/router`: route definitions
- `docs`: project-specific supporting notes
