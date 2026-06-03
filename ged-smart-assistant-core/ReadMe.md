# ged-smart-assistant-core

#### Description

`ged-smart-assistant-core` is the backend API that orchestrates authentication, session handling, AI inference, and document actions for the GED Smart Assistant. It receives chat requests, calls the AI service to identify the intended action, and then executes that action against the MiniGED API.

#### Architecture Role

This repository is the orchestration backend of the platform. It acts as the main application API between the UI layer and the downstream services, especially `ai-service` and `ged-smart-assistant-mini-GED`.

#### Features

- Exposes assistant chat endpoints for the frontend
- Manages login, session lookup, and logout against MiniGED
- Calls the AI inference service to classify user intent
- Creates documents in MiniGED when the inferred tool is `create_document`
- Searches MiniGED documents when the inferred tool is `search_documents`
- Provides Swagger/OpenAPI support in development

#### Tech Stack

- C#
- ASP.NET Core Web API
- .NET 10
- Swagger / Swashbuckle
- `HttpClientFactory`
- OpenAPI support via `Microsoft.AspNetCore.OpenApi`

#### Installation

Prerequisites:

- .NET SDK 10
- Running instances of `ai-service` and `ged-smart-assistant-mini-GED`

Restore dependencies:

```bash
dotnet restore GedSmartAssistant.Api\GedSmartAssistant.Api.csproj
```

Configuration:

- `AiService:BaseUrl`: base URL of the AI inference service
- `MiniGed:BaseUrl`: base URL of the MiniGED backend

These settings are defined in `GedSmartAssistant.Api/appsettings.json` and can also be overridden through standard ASP.NET Core environment variables:

- `AiService__BaseUrl`
- `MiniGed__BaseUrl`

#### Usage

Run the API locally:

```bash
dotnet run --project GedSmartAssistant.Api\GedSmartAssistant.Api.csproj
```

By default, development settings point to:

- AI service: `http://localhost:8000`
- MiniGED backend: `https://localhost:5092`

Swagger UI is enabled in development.

#### API / Integration

- `POST /api/Auth/login`: authenticates a user against MiniGED
- `GET /api/Auth/me`: returns the current authenticated MiniGED user
- `POST /api/Auth/logout`: clears the current session
- `POST /api/Chat`: processes a natural-language request through the assistant workflow

Service integrations:

- Calls `ai-service` at `/infer`
- Calls MiniGED endpoints such as `/api/Account/login`, `/api/Account/me`, `/api/Document/add`, and `/api/document/search`

#### Project Structure

- `GedSmartAssistant.Api/Controllers`: HTTP endpoints for auth and chat
- `GedSmartAssistant.Api/Services`: AI client, MiniGED client, chat orchestration, and session services
- `GedSmartAssistant.Api/Models`: configuration, auth, AI, and document models
- `GedSmartAssistant.Api/Dtos`: request and response contracts
- `GedSmartAssistant.Api/Interfaces`: service abstractions
- `GedSmartAssistant.Api/Program.cs`: application bootstrap and dependency registration
