# ARGUS Optimization Service (Python VRP Solver)

FastAPI-based Vehicle Routing Problem (VRP) solver using Google OR-Tools. This service optimizes fleet routes for waste collection, handling multi-vehicle, multi-destination scenarios with capacity constraints, service times, and priority-based destination handling.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Local Setup](#local-setup)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [Docker Deployment](#docker-deployment)
- [Optimization Modes](#optimization-modes)
- [Performance Tuning](#performance-tuning)
- [Troubleshooting](#troubleshooting)

## Overview

The ARGUS Optimization Service solves Vehicle Routing Problems for waste truck fleet management. It accepts:

- **Vehicles**: Fleet units with start locations and capacity constraints
- **Destinations**: Pickup/delivery locations with demand, priority, and service times
- **Distance Matrix**: Real-world distances/durations (Mapbox or Haversine fallback)
- **Constraints**: Route duration limits, mandatory destination (depot), low-volume skipping

Returns optimized routes with:
- Waypoint sequences per vehicle
- Total distance and duration estimates
- Cost calculations (fixed vehicle cost + per-minute travel + service time)
- Solver metadata (duration, optimality status)

## Features

- **Multi-Mode Optimization**:
  - `daily_plan`: Full day optimization (up to 30s solver time)
  - `swarm_recovery`: Emergency rerouting (<5s response time, <60ms SLA)

- **Constraint Handling**:
  - Vehicle capacity limits
  - Route time constraints
  - Service time windows
  - Priority-based destination handling
  - Low-volume destination skip logic

- **Mock Mode**: Stubbed responses for development/testing without OR-Tools overhead

- **Graceful Degradation**: Fallback strategies when optimization constraints cannot be satisfied

- **Comprehensive Logging**: Structured logging with request/response tracing

## Architecture

```
FastAPI Application
    │
    ├─ /health endpoint (service readiness)
    │
    ├─ /solve endpoint
    │   ├─ Input validation (vehicle, destination, distance matrix)
    │   ├─ Route constraint building (distance callbacks, dimensions)
    │   ├─ Model creation (routing index manager, routing object)
    │   │
    │   ├─ MOCK_MODE=true
    │   │   └─ Stub response generator (for testing)
    │   │
    │   └─ MOCK_MODE=false
    │       ├─ OR-Tools solver (first solution strategy + metaheuristic)
    │       ├─ Result parsing
    │       └─ Cost calculation
    │
    └─ Exception handlers (validation errors, empty inputs, solver timeout)
```

### Core Components

| Component | Purpose |
|-----------|---------|
| `model_builder.py` | Constructs OR-Tools routing model from request data |
| `vrp_solver.py` | Executes OR-Tools solver with configurable strategies and time limits |
| `result_parser.py` | Parses solution into route sequences, costs, and metadata |
| `schemas/request.py` | Request validation (Pydantic models) |
| `schemas/response.py` | Response schema with routes and solver metrics |
| `mock/stub_responses.py` | Development stubs (mock mode) |
| `core/exceptions.py` | Custom exception handlers |
| `core/logging_config.py` | Structured logging setup |

## Prerequisites

### Required

- **Python** 3.10 or higher
- **pip** or **poetry** for dependency management
- **Google OR-Tools** 9.15+ (automatically installed via requirements.txt)

### Optional

- **Docker** 20.10+ and **Docker Compose** 2.0+ (for containerized deployment)

## Local Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd python
```

### 2. Create Virtual Environment

```bash
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your settings
```

### 5. Run Development Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Server available at `http://localhost:8001`
API docs at `http://localhost:8001/docs` (Swagger UI)

### 6. Run Tests

```bash
pytest -v
pytest --cov=app
```

## Configuration

### Environment Variables

```
# Server
PORT=8001                              # HTTP server port
HOST=0.0.0.0                          # Bind address
MOCK_MODE=true                        # Enable stub mode (true/false)
LOG_LEVEL=INFO                        # Logging level (DEBUG, INFO, WARNING, ERROR)

# Optimization
SOLVER_TIME_LIMIT_DAILY_MS=30000      # Daily plan optimization timeout (ms)
SOLVER_TIME_LIMIT_RECOVERY_MS=5000    # Swarm recovery optimization timeout (ms)

# Cost Parameters
LOW_VOLUME_SKIP_PENALTY=100           # Penalty for skipping low-volume destination
MANDATORY_PENALTY=1_000_000           # Penalty for unfeasible mandatory destination
```

### .env.example

```
PORT=8001
HOST=0.0.0.0
MOCK_MODE=false
LOG_LEVEL=INFO
SOLVER_TIME_LIMIT_DAILY_MS=30000
SOLVER_TIME_LIMIT_RECOVERY_MS=5000
LOW_VOLUME_SKIP_PENALTY=100
MANDATORY_PENALTY=1000000
```

## API Endpoints

### GET /health

Liveness probe and service status.

**Response:**
```json
{
  "status": "ok",
  "ortoolsVersion": "9.11+",
  "mockMode": false
}
```

### POST /solve

Optimize vehicle routes.

**Request Body:**

```json
{
  "mode": "daily_plan",
  "vehicles": [
    {
      "id": "vehicle_1",
      "startLat": -6.175,
      "startLng": 106.827,
      "capacityKg": 5000,
      "currentLoadKg": 2000
    }
  ],
  "destinations": [
    {
      "id": "tpa_1",
      "type": "TPA",
      "lat": -6.180,
      "lng": 106.830,
      "demandKg": 1500,
      "priority": 1,
      "serviceMinutes": 15,
      "historicalVolumeAvg": 80.0,
      "lowVolumeFlag": false
    }
  ],
  "distanceMatrix": {
    "mode": "mapbox",
    "rows": [
      {
        "from": "vehicle_1",
        "to": "tpa_1",
        "meters": 1200,
        "seconds": 180
      }
    ]
  },
  "constraints": {
    "maxRouteMinutes": 480,
    "finalDepotId": "vehicle_1",
    "skipLowVolume": true
  }
}
```

**Response:**

```json
{
  "status": "OPTIMAL",
  "routes": [
    {
      "vehicleId": "vehicle_1",
      "waypoints": ["vehicle_1", "tpa_1"],
      "totalDistanceMeters": 2400,
      "totalDurationSeconds": 360,
      "totalDemandKg": 1500,
      "costInfo": {
        "fixedVehicleCostUsd": 50.0,
        "travelCostUsd": 12.0,
        "serviceCostUsd": 3.75,
        "totalCostUsd": 65.75
      }
    }
  ],
  "solverDurationMs": 245,
  "solverTimeLimitMs": 30000,
  "unvisitedDestinations": [],
  "timestamp": 1719921600
}
```

**Request Parameters:**

| Field | Type | Description |
|-------|------|-------------|
| `mode` | string | `daily_plan` or `swarm_recovery` |
| `vehicles` | array | Fleet with `id`, `startLat`, `startLng`, `capacityKg`, `currentLoadKg` |
| `destinations` | array | Pickups/deliveries with `id`, `type`, `lat`, `lng`, `demandKg`, `priority`, `serviceMinutes`, `historicalVolumeAvg`, `lowVolumeFlag` |
| `distanceMatrix` | object | Mapbox or haversine distances between all points |
| `constraints` | object | `maxRouteMinutes`, `finalDepotId` (mandatory return location), `skipLowVolume` |

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `OPTIMAL`, `FEASIBLE`, or `INFEASIBLE` |
| `routes` | array | Optimized routes per vehicle |
| `solverDurationMs` | int | Actual solver execution time |
| `solverTimeLimitMs` | int | Configured time limit |
| `unvisitedDestinations` | array | Destinations not included in solution |
| `timestamp` | int | Unix timestamp (response generation time) |

## Usage Examples

### Daily Route Optimization

```bash
curl -X POST http://localhost:8001/solve \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "daily_plan",
    "vehicles": [...],
    "destinations": [...],
    "distanceMatrix": {...},
    "constraints": {...}
  }'
```

### Swarm Recovery (Emergency Rerouting)

```bash
curl -X POST http://localhost:8001/solve \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "swarm_recovery",
    "vehicles": [...],
    "destinations": [...],
    "distanceMatrix": {...},
    "constraints": {...}
  }'
```

### Testing with Mock Mode

Set `MOCK_MODE=true` in `.env` to get instant responses without OR-Tools overhead.

## Docker Deployment

### Development Environment

```bash
docker build -t argus-solver:latest -f Dockerfile .
docker run -d \
  --name argus-solver \
  -p 8001:8001 \
  -e MOCK_MODE=false \
  argus-solver:latest
```

Or use Docker Compose for full stack:

```bash
docker-compose up -d
```

### Production Deployment

Build optimized image:

```bash
docker build -t argus-solver:prod -f Dockerfile .
```

Run with environment:

```bash
docker run -d \
  --name argus-solver-prod \
  -p 8001:8001 \
  -e MOCK_MODE=false \
  -e LOG_LEVEL=WARNING \
  -e SOLVER_TIME_LIMIT_DAILY_MS=25000 \
  argus-solver:prod
```

Or use docker-compose.prod.yml:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Dockerfile Features

- **Multi-stage build**: Separate dependencies and runtime stages
- **Python 3.11 Slim**: Lightweight base image
- **Non-root user**: Runs as `appuser` for security
- **Health check**: Built-in readiness monitoring
- **Optimized layers**: Minimal image size (~400MB)

Image size: ~400MB | Build time: ~3-5 minutes

## Optimization Modes

### Daily Plan (`daily_plan`)

- **Use Case**: Full-day route planning for waste collection
- **Time Limit**: 30 seconds (configurable via `SOLVER_TIME_LIMIT_DAILY_MS`)
- **Strategy**: First solution (PATH_CHEAPEST_ARC) + Guided Local Search (if >15 nodes)
- **Goal**: Minimize total distance/cost with best quality

**Typical Flow:**
1. Generate initial feasible solution quickly
2. Iteratively improve using GLS metaheuristic
3. Return best solution found within time limit

### Swarm Recovery (`swarm_recovery`)

- **Use Case**: Emergency rerouting when a vehicle breaks down
- **Time Limit**: 5 seconds (configurable via `SOLVER_TIME_LIMIT_RECOVERY_MS`)
- **SLA**: <60ms response in production, optimized for speed
- **Strategy**: First solution only (for small problem size ~3-5 vehicles)
- **Goal**: Redistribute broken vehicle's load to healthy vehicles ASAP

**Typical Flow:**
1. Quickly find any feasible solution
2. Return immediately (no metaheuristic polish)
3. Accept suboptimal but valid routes for speed

## Performance Tuning

### Solver Time Limits

Adjust based on problem size and requirements:

```
Small (≤10 vehicles, ≤20 destinations): 5-10s
Medium (≤30 vehicles, ≤50 destinations): 20-30s
Large (>30 vehicles, >50 destinations): 45-60s
```

### Metaheuristic Tuning

Currently uses **Guided Local Search (GLS)** for problems with ≥15 nodes.

For faster responses (more exploration needed):
- Increase metaheuristic `time_limit_ms`
- Switch to `SIMULATED_ANNEALING` for faster convergence on large problems

### Model Builder Optimization

Performance depends on:
- Number of vehicles (scales linearly)
- Number of destinations (scales quadratically with distance matrix)
- Distance matrix sparsity (fewer nonzero entries = faster)

### Caching Strategies

- **Distance Matrix Caching** (backend responsibility):
  - Cache Mapbox responses with 1-hour TTL
  - Use geohash-based bucketing for similar location requests

- **Solution Caching**:
  - Cache daily plans (reuse if fleet/destination set unchanged)
  - Invalidate on new telemetry or vehicle status changes

## Troubleshooting

### Solver Returns INFEASIBLE

```
"status": "INFEASIBLE"
```

**Causes:**
- Total demand exceeds total vehicle capacity
- Route time limit too restrictive for distance
- Destination unreachable given constraints

**Solutions:**
- Increase vehicle capacity or count
- Relax `maxRouteMinutes` constraint
- Lower destination priority/service time
- Enable `skipLowVolume` to exclude non-critical stops

### Slow Solver Response

**Symptoms:** Response time >30s in daily_plan mode

**Solutions:**
- Check `SOLVER_TIME_LIMIT_DAILY_MS` (too high?)
- Reduce problem size (pre-filter low-priority destinations)
- Check OR-Tools version (upgrade if outdated)
- Verify distance matrix completeness (missing entries cause solver overhead)

### Memory Issues

```
MemoryError or OutOfMemory exception
```

**Solutions:**
- Reduce vehicle/destination count per request
- Split large problems into multiple solve calls
- Increase Docker memory limit: `--memory 2g`
- Use swarm_recovery mode (smaller problems, faster GC)

### High CPU Usage

**Symptoms:** Container CPU 100% sustained

**Solutions:**
- Lower `SOLVER_TIME_LIMIT_DAILY_MS` to force earlier termination
- Enable MOCK_MODE for testing (no CPU overhead)
- Use `swarm_recovery` mode (5s limit, faster)
- Monitor with `docker stats`

### OR-Tools Errors

```
ImportError: No module named ortools
```

**Solution:**
```bash
pip install --upgrade ortools
# Or in Docker: rebuild image
docker build --no-cache -t argus-solver:latest .
```

### Validation Errors

```json
{
  "detail": [
    {
      "loc": ["body", "vehicles"],
      "msg": "vehicles must not be empty",
      "type": "validation_error"
    }
  ]
}
```

**Solution:** Ensure all required fields in request match schema:
- Vehicles: `id`, `startLat`, `startLng`, `capacityKg`, `currentLoadKg`
- Destinations: `id`, `type`, `lat`, `lng`, `demandKg`, `priority`, `serviceMinutes`, `historicalVolumeAvg`, `lowVolumeFlag`
- Distance Matrix: `mode`, `rows` with `from`, `to`, `meters`, `seconds`
- Constraints: `maxRouteMinutes`, `finalDepotId`, `skipLowVolume`

## API Documentation

Interactive API docs available at:
- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`

## Development

### Run Tests

```bash
pytest -v
pytest --cov=app --cov-report=html
```

### Lint & Format

```bash
black app/
flake8 app/
pylint app/
```

### Debug Mode

```bash
LOG_LEVEL=DEBUG uvicorn main:app --reload
```

This enables detailed logging for each solver step.

## License

UNLICENSED — Proprietary software
