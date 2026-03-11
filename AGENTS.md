# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenClaw Watchboard is a comprehensive security monitoring dashboard for tracking OpenClaw-related security risks. The application consists of three main monitoring components:

1. **OpenClaw Top 10 Risks** - Real-time display of critical security vulnerabilities and threats
2. **Public Exposure Analysis** - Visualization dashboard for internet-exposed OpenClaw services
3. **Skill Poisoning Detection** - Management system for trusted Skills and malicious Skill detection

## Architecture

This is a **monorepo** with TypeScript throughout:

```
openclaw-watchboard/
├── frontend/          # React 19 + Ant Design Pro application
├── backend/           # Node.js Express API server
├── shared/           # Shared TypeScript types and utilities
├── docs/             # Project documentation
└── package.json      # Monorepo workspace configuration
```

### Technology Stack

**Frontend:**
- React 19 with TypeScript
- Ant Design Pro (enterprise UI framework)
- UmiJS application framework
- Ant Design Charts for data visualization
- Development server runs on port 3000

**Backend:**
- Node.js + Express + TypeScript
- SQLite database with TypeORM
- RESTful API design
- Node-cron for scheduled tasks
- Development server runs on port 3001

**Shared:**
- TypeScript type definitions
- Common constants and utilities
- API interfaces and data models

## Development Commands

### Initial Setup
```bash
# Install all dependencies across the monorepo
npm run install:all

# Copy and configure environment variables
cp .env.example .env
```

### Development
```bash
# Start both frontend and backend in development mode
npm run dev

# Start services individually
npm run dev:frontend    # React dev server (port 3000)
npm run dev:backend     # Express API server (port 3001)
```

### Building
```bash
# Build all components
npm run build

# Build individual components
npm run build:frontend
npm run build:backend
npm run build:shared
```

### Testing & Quality
```bash
npm test               # Run all tests
npm run lint          # ESLint across all packages
npm run lint:fix      # Auto-fix linting issues
```

### Production
```bash
npm start             # Start production server
```

## Core API Routes

The backend implements three main API route groups:

### Risk Management (`/api/risks`)
- `GET /api/risks/top10` - Fetch OpenClaw Top 10 security risks
- `GET /api/risks/:riskId` - Get detailed risk information
- `GET /api/risks/stats/summary` - Risk statistics overview
- `GET /api/risks/trends/:timeRange` - Risk trend analysis
- `POST /api/risks/refresh` - Trigger risk data refresh

### Exposure Analysis (`/api/exposure`)
- `GET /api/exposure/overview` - Public exposure summary dashboard
- `GET /api/exposure/services` - List of exposed services
- `GET /api/exposure/geography` - Geographic distribution data
- `GET /api/exposure/ports` - Port distribution statistics
- `GET /api/exposure/trends` - Exposure trends over time
- `POST /api/exposure/scan` - Initiate security scanning

### Skill Management (`/api/skills`)
- `GET /api/skills/trusted` - Verified trusted Skill library
- `GET /api/skills/suspicious` - Detected suspicious/malicious Skills
- `GET /api/skills/analysis/:skillId` - Detailed Skill security analysis
- `POST /api/skills/trusted` - Add Skill to trusted list
- `POST /api/skills/report` - Report suspicious Skill
- `POST /api/skills/verify` - Initiate Skill security verification

## Key Components & Architecture Patterns

### Backend Controllers
Located in `backend/src/controllers/`:
- `RiskController` - Manages security risk data and analysis
- `ExposureController` - Handles public exposure monitoring and scanning
- `SkillController` - Manages Skill verification and threat detection

### Frontend Pages (Ant Design Pro)
The frontend uses Ant Design Pro's layout system with three main dashboard sections:
1. Risk monitoring page with charts and detailed risk analysis
2. Geographic visualization page for exposure mapping
3. Skill management interface with trust/report functionality

### Shared Types
`shared/src/types/index.ts` contains TypeScript interfaces for:
- Risk data structures (`Risk`, `RiskStats`)
- Exposure monitoring (`ExposedService`, `GeographicData`)
- Skill management (`TrustedSkill`, `SuspiciousSkill`, `SkillAnalysis`)
- API response patterns (`ApiResponse`, `PaginatedResponse`)

## Development Patterns

### API Development
- All API responses use the standardized `ApiResponse<T>` interface
- Controllers use async/await with proper error handling
- Express middleware handles CORS, rate limiting, and security headers
- Routes are organized by functional domain (risks, exposure, skills)

### Frontend Development
- Uses Ant Design Pro's ProComponents for consistent enterprise UI
- State management through built-in UmiJS data flow
- Charts implemented with @ant-design/charts
- TypeScript strict mode enabled throughout

### Error Handling
- Backend uses centralized error middleware (`errorHandler`)
- Frontend displays user-friendly error messages via Ant Design notifications
- API errors include proper HTTP status codes and structured error objects

## Database & Data Sources

### Local Storage
- SQLite database for application data and caching
- TypeORM entities for data modeling
- Database migrations for schema management

### External Data Sources
- OpenClaw API integration for vulnerability data
- CVE feeds for security intelligence
- Community Skill repositories for verification
- Network scanning tools (nmap, masscan) for exposure detection

## Security Considerations

- Rate limiting on all API endpoints
- Input validation and sanitization
- CORS policies configured for frontend-backend communication
- Environment variable configuration for sensitive credentials
- Security scanning integration for Skill verification

## Environment Configuration

Key environment variables (see `.env.example`):
- `OPENCLAW_API_URL` and `OPENCLAW_API_KEY` - OpenClaw service integration
- `THREAT_INTEL_FEEDS` - External threat intelligence sources
- `SKILL_REPO_URLS` - Trusted Skill repository locations
- Database and Redis connection strings
- SMTP configuration for alerting

## Adding New Features

When extending the dashboard:

1. **New Risk Types**: Extend the Risk interface in `shared/src/types/` and add corresponding API endpoints
2. **New Visualization**: Add chart components using @ant-design/charts in the frontend
3. **New Data Sources**: Implement service classes in `backend/src/services/`
4. **New Skill Detection**: Extend SkillController with new analysis methods

## Common Development Tasks

### Adding a New API Endpoint
1. Define the route in the appropriate router file (`backend/src/routes/`)
2. Implement the controller method with proper TypeScript types
3. Add the endpoint to the corresponding interface in `shared/src/types/`
4. Update frontend API calls to use the new endpoint

### Adding New Data Visualization
1. Use Ant Design Charts components in the frontend
2. Ensure data follows the shared type interfaces
3. Implement responsive design for dashboard layouts
4. Add proper loading and error states

### Extending Security Analysis
1. Add new analysis algorithms to the appropriate controller
2. Define new threat detection patterns
3. Update the SkillAnalysis interface to include new metrics
4. Implement frontend display for new analysis results