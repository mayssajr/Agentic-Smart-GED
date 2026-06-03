# ged-smart-assistant-mini-GED

#### Description

`ged-smart-assistant-mini-GED` contains document management application used by the assistant. It includes a Vue frontend for users and an ASP.NET Core backend that handles authentication, document management, file processing, background jobs, and PostgreSQL-backed full-text search (instead of meilisearch ).

#### Architecture Role

This repository is the primary domain application of the system. It provides the GED functionality that the assistant layer builds on top of, including user accounts, documents, files, tasks, and search operations.

#### Features

- User registration, login, and profile retrieval
- Document CRUD endpoints
- File upload and file-related document handling
- PostgreSQL full-text search with file-level results and filters
- Background processing with Hangfire
- Vue-based frontend for authentication, dashboard, documents, users, profile, and tasks
- Dockerization for PostgreSQL and to manage the database : Adminer

#### Tech Stack

- C#
- ASP.NET Core Web API
- .NET 8
- Entity Framework Core
- PostgreSQL (`Npgsql`)
- Hangfire with SQLite storage
- Swagger / Swashbuckle
- Vue 3
- Vite
- Pinia
- Axios

#### Installation

Prerequisites:

- .NET SDK 8
- Node.js 18+ and npm
- PostgreSQL

Backend setup:

```bash
dotnet restore MiniGED.Backend\MiniGED.API.csproj
```

Frontend setup:

```bash
cd MiniGED-Frontend
npm install
```

Frontend environment file:

```bash
cd MiniGED-Frontend
copy .env.example .env
```

Then edit `MiniGED-Frontend/.env` and set `VITE_API_BASE_URL` to your backend URL, for example:

```env
VITE_API_BASE_URL=http://localhost:5092/api
```

Configuration:

- `ConnectionStrings:DefaultConnection`: PostgreSQL connection string
- `ConnectionStrings:HangfireConnection`: Hangfire SQLite database path
- `Jwt:Key`
- `Jwt:Issuer`
- `Jwt:ExpiresInMinutes`
- `MiniGED-Frontend/.env`: frontend runtime config

#### Usage

Run the backend:

```bash
dotnet run --project MiniGED.Backend\MiniGED.API.csproj
```

Run the frontend in a separate terminal:

```bash
cd MiniGED-Frontend
npm run dev
```

The frontend runs with Vite, and the backend exposes Swagger in development.

#### API / Integration

Representative backend endpoints:

- `POST /api/Account/register`
- `POST /api/Account/login`
- `GET /api/Account/me`
- `POST /api/Document/add`
- `GET /api/Document`
- `GET /api/Document/{id}`
- `PUT /api/Document/{id}`
- `DELETE /api/Document/{id}`
- `POST /api/document/search`

Search request body supports:

- `query`
- `documentIds`
- `fileStatuses`
- `uploadedFrom`
- `uploadedTo`
- `taskStatuses`
- `taskPriorities`
- `taskDueFrom`
- `taskDueTo`
- `page`
- `pageSize`
- `sort`

#### Project Structure

- `MiniGED.Backend/Controllers`: account, document, task, role, user, and file endpoints
- `MiniGED.Backend/Services`: token, password, file processing, text extraction, search, and seed services
- `MiniGED.Backend/Data`: Entity Framework database context
- `MiniGED.Backend/Models`: domain entities
- `MiniGED.Backend/Dtos`: API contracts
- `MiniGED-Frontend/src/views`: page-level Vue views
- `MiniGED-Frontend/src/components`: reusable UI components
- `MiniGED-Frontend/src/services`: frontend API access layer
- `docker-compose.yml`: local infrastructure definition
