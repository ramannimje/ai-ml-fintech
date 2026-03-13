# Market Intelligence Upgrade Plan

## Phase 1: Current Architecture Assessment

### Current architecture summary

The active application is a single FastAPI backend in `app/` with a React/Vite frontend in `frontend/`. `backend/main.py` is only a thin wrapper around `app.main`; `backend/app/` and `src/` are legacy/duplicate trees and are not the main runtime path. The backend currently combines data ingestion, normalization, feature engineering, model training, inference, alerts, and AI chat orchestration inside service classes, especially [`app/services/commodity_service.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/app/services/commodity_service.py).

### Component map

- Frontend
  - React + TypeScript + Vite entrypoint in [`frontend/src/main.tsx`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/frontend/src/main.tsx)
  - Router shell in [`frontend/src/App.tsx`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/frontend/src/App.tsx)
  - API client in [`frontend/src/api/client.ts`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/frontend/src/api/client.ts)
  - Main product views:
    - dashboard [`frontend/src/pages/dashboard.tsx`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/frontend/src/pages/dashboard.tsx)
    - commodity detail [`frontend/src/pages/commodity.tsx`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/frontend/src/pages/commodity.tsx)
    - AI assistant [`frontend/src/pages/chat.tsx`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/frontend/src/pages/chat.tsx)
    - training console [`frontend/src/pages/train.tsx`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/frontend/src/pages/train.tsx)

- Backend API
  - App bootstrap in [`app/main.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/app/main.py)
  - Market, alerts, profile, train routes in [`app/api/routes.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/app/api/routes.py)
  - AI routes in [`app/api/routes_ai_chat.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/app/api/routes_ai_chat.py)
  - Settings routes in [`app/api/routes_settings.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/app/api/routes_settings.py)

- Data and ML
  - Historical fetcher and cache in [`ml/data/data_fetcher.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/ml/data/data_fetcher.py)
  - Feature engineering in [`ml/features/engineer.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/ml/features/engineer.py)
  - Model training candidates in [`ml/training/models.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/ml/training/models.py)
  - Artifact persistence in [`ml/inference/artifacts.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/ml/inference/artifacts.py)

- AI and reasoning
  - Context parsing and deterministic reasoning in [`app/services/ai_reasoning_engine.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/app/services/ai_reasoning_engine.py)
  - OpenRouter integration in [`app/services/ai_chat_service.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/app/services/ai_chat_service.py)
  - Vector retrieval in [`app/services/vector_service.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/app/services/vector_service.py)

- Persistence
  - Async SQLAlchemy session in [`app/db/session.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/app/db/session.py)
  - Runtime schema repair in [`app/db/schema_guard.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/app/db/schema_guard.py)
  - Core tables: training runs, alerts, user profile/settings, chat history, vector tables in `app/models/`

### Data flow map

1. Frontend requests `/api/live-prices`, `/api/historical`, `/api/predict`, `/api/ai/chat`, `/api/train`.
2. [`CommodityService`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/app/services/commodity_service.py) fetches live data from `metals.live`, then direct Yahoo HTTP, then cached history, then placeholders.
3. Historical data is fetched through [`MarketDataFetcher.get_historical`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/ml/data/data_fetcher.py), cached to `ml/cache/*.csv`, and converted to regional units/currencies in the service layer.
4. Feature engineering runs inline via [`add_features`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/ml/features/engineer.py) plus service-side proxy features for FX, inflation, and rates.
5. Training is initiated through `/api/train/*`, runs in FastAPI background tasks, benchmarks several model families, then stores metadata in `training_runs` and artifacts in `ml/artifacts/`.
6. Prediction loads the latest artifact, generates a point forecast and confidence band, or falls back to a naive forecast if the model path fails.
7. AI chat parses intent, rebuilds market context from live/historical/predict endpoints, optionally retrieves vector documents, then prompts OpenRouter Qwen; deterministic reasoning is the fallback.

### Deployment and runtime structure

- Local development
  - Backend: `uvicorn app.main:app --reload --port 8000`
  - Frontend: `cd frontend && npm run dev`
  - Vite proxies `/api` to FastAPI

- Containers
  - Compose stack in [`docker-compose.yml`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/docker-compose.yml)
  - Services: backend, frontend, postgres+pgvector, redis, nginx
  - Nginx routes `/api/*` to backend and `/` to frontend

- Background work
  - Model training uses FastAPI `BackgroundTasks`
  - WhatsApp alert worker starts inside backend process on app startup
  - No dedicated scheduler or separate worker deployment for ingestion/backfills

### Key technical debt, gaps, bottlenecks, risks

- Ingestion, ETL, features, forecasting, and serving are tightly coupled in request-path service methods.
- No durable raw ingestion zone, normalized time-series store, or provenance-first schema.
- Background training is in-memory and process-local; status cache is lost on restart.
- Model registry is effectively the latest `training_runs` row plus filesystem artifact path.
- Macro features are proxy-derived; there is no first-class macro feed ingestion.
- News ingestion is pull-on-demand and not deduplicated or persisted as a normalized dataset.
- AI reasoning still reconstructs context ad hoc instead of consuming a stable signal contract.
- Duplicate repo trees (`backend/app`, `src/`) increase ambiguity and maintenance risk.

## Phase 2: Target Architecture

### Target layers

1. Data ingestion
   - Provider adapters for market prices, macro feeds, and news
   - Source health scoring, cooldowns, fallback ordering, rate-limit aware retries
   - Idempotent writes keyed by source, symbol, timestamp

2. ETL / normalization
   - Raw zone for unmodified payloads
   - Canonical normalized series for prices, macro metrics, and news entities
   - Provenance, source timestamp, ingest timestamp, validation status on every record
   - Backfill and replay jobs separated from online serving

3. Feature engineering
   - Materialized feature tables keyed by commodity, region, timestamp, horizon
   - Technical, macro, calendar, FX, and news-derived features
   - Offline generation for training and online generation for near-real-time serving

4. Forecasting
   - Baseline naive/statistical models
   - Tree-based models and optional time-series foundation models
   - Backtesting, model versioning, promotion rules, drift and performance monitoring

5. Signal generation
   - Convert forecasts into directional signals, confidence, scenarios, and explanation metadata
   - Business thresholds separated from model outputs

6. Qwen reasoning
   - Reasoning consumes structured signals, macro context, and curated news summaries
   - Deterministic schemas for prompt input/output
   - Traceable prompt assembly with provenance and guardrails

7. API and dashboard
   - Separate APIs for raw/normalized data, features, forecasts, and signals
   - Dashboard reads signals/intelligence bundles, not model internals
   - Caching around normalized snapshots and signal payloads

### Phase 2 execution in this repo

The next concrete step in this repository is not a platform rewrite. It is an internal service-boundary extraction under the existing FastAPI routes in `app/api/routes.py`.

For this slice, Phase 2 maps to:

1. Ingestion boundary
   - Extract live-price fallback logic from `CommodityService` into a dedicated ingestion layer with explicit provider adapters
   - Keep `metals.live`, Yahoo Finance HTTP, cached-history, and placeholder fallback behavior intact
   - Attach first-class provenance metadata to normalized quote results instead of carrying source strings only at API formatting time

2. Normalization boundary
   - Introduce explicit normalized contracts for:
     - canonical live quotes
     - canonical historical OHLCV series
     - provenance metadata
   - Centralize transformation from canonical USD/troy_oz data into region-specific API responses

3. Feature materialization boundary
   - Move feature enrichment out of `CommodityService` request logic into a dedicated feature store/materialization service
   - Preserve current technical and proxy macro features while making the materialization step reusable by forecasting and intelligence services

4. Migration rule for current APIs
   - Keep `/api/live-prices`, `/api/historical`, `/api/predict`, `/api/intelligence`, and AI chat flows stable
   - Use `CommodityService` as a compatibility facade while internal responsibilities move behind dedicated services

## Phase 3: Repository-grounded migration map

### Reuse

- Reuse `app/main.py`, auth, DB session, current API router structure
- Reuse `ml/data`, `ml/features`, `ml/training`, `ml/inference` as the initial ML core
- Reuse `CommodityService` for current endpoints while extracting staged orchestration into smaller services
- Reuse vector, news, and alert subsystems with clearer boundaries

### Refactor

- Refactor `CommodityService` into orchestration over dedicated ingestion/feature/forecast services
- Refactor AI reasoning to depend on structured signal bundles
- Refactor background training into queueable jobs with persistent state

### Phase 3 mapping for the next incremental slice

- `app/services/commodity_service.py`
  - keep as the public orchestration facade for existing routes
  - remove direct ownership of provider fallback and feature materialization

- `app/services/ingestion_service.py`
  - add provider abstraction for live-price ingestion
  - add canonical historical series loading wrapper over `ml/data/data_fetcher.py`
  - own source ordering, fallback labeling, and provenance generation

- `app/services/normalization_service.py`
  - convert canonical market data contracts into existing API response schemas
  - keep regional conversion rules in one place instead of duplicating them across request handlers

- `app/services/feature_store_service.py`
  - own online feature materialization from canonical historical series
  - expose enriched DataFrame output for training/inference and stable snapshots for market intelligence

- `app/schemas/market_data.py`
  - define explicit normalized internal contracts for quotes, OHLCV rows, series, and provenance

- `app/services/market_signal_service.py`
  - stop reaching into `CommodityService.fetcher` and `CommodityService._enrich_features`
  - consume the extracted ingestion and feature services directly

### Add

- `app/services/market_signal_service.py`
- Future modules:
  - `app/services/ingestion_service.py`
  - `app/services/normalization_service.py`
  - `app/services/feature_store_service.py`
  - `app/services/model_registry_service.py`
  - `app/services/signal_service.py`

### Proposed service boundaries

- Ingestion: source adapters, cooldowns, rate limits, raw payload capture
- ETL: canonical schemas and validation
- Features: point-in-time feature materialization
- Forecasting: train, load, infer, backtest
- Signals: thresholding, confidence, ranking, explainability
- Reasoning: prompt contracts and structured output
- API/dashboard: presentation only

## Phase 4: Incremental implementation delivered in this change

### What changed

- Added a structured intelligence contract and service:
  - [`app/services/market_signal_service.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/app/services/market_signal_service.py)
  - new response models in [`app/schemas/responses.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/app/schemas/responses.py)
- Added `GET /api/intelligence/{commodity}/{region}` in [`app/api/routes.py`](/Users/ramannimje/Documents/Coding/github/ai-ml-fintech/app/api/routes.py)
- Updated AI reasoning path to attach structured signal bundles before LLM prompting

### Why this is the right first step

This change does not rewrite the app. It creates the first explicit boundary between raw market mechanics and downstream interpretation. The dashboard and chat layer can now consume a structured market-intelligence object with provenance, engineered features, signal classification, and forecast context. That is the right bridge from the current monolith toward the target production architecture.

## Phase 5: Incremental implementation delivered in the next slice

### What changes in this slice

- Add explicit normalized market-data contracts in `app/schemas/market_data.py`
- Add:
  - `app/services/ingestion_service.py`
  - `app/services/normalization_service.py`
  - `app/services/feature_store_service.py`
- Rewire `CommodityService` to orchestrate these services while keeping route contracts unchanged
- Rewire `MarketSignalService` to consume extracted ingestion and feature boundaries instead of `CommodityService` internals
- Extend tests around provider fallback, provenance, and feature materialization

### Why this slice is next

This is the narrowest useful Phase 2 implementation that creates durable boundaries for ingestion, normalization, and features without destabilizing forecasting, AI chat, or existing APIs. It moves the codebase from "one service does everything" to "one facade orchestrates explicit subsystems", which is the correct Phase 3 migration path for this repository.

## Phase 6: Incremental implementation delivered in the forecast/registry slice

### What changes in this slice

- Add:
  - `app/services/model_registry_service.py`
  - `app/services/forecast_service.py`
- Move latest-run lookup, artifact loading, and warmed-model cache ownership out of `CommodityService`
- Move prediction generation, horizon adaptation, confidence-band construction, and naive fallback forecasting out of `CommodityService`
- Keep `CommodityService.latest_metrics()`, `CommodityService.prewarm_latest_models()`, and `CommodityService.predict()` as compatibility facades over the extracted services

### Why this slice matters

This finishes the core online serving split for the current backend path. The existing service facade still powers the APIs, but ingestion, normalization, features, model lookup, and forecasting are now separate runtime concerns. That is the minimum viable service decomposition before background training/jobs and richer provenance-aware APIs can be extracted cleanly.

## Phase 7: Incremental implementation delivered in the training slice

### What changes in this slice

- Add `app/services/training_service.py`
- Move model benchmark selection, artifact persistence, metadata insert, and in-memory training status tracking out of `CommodityService`
- Keep `CommodityService.train()` and `CommodityService.get_training_status()` as compatibility wrappers over the extracted training service

### Why this slice matters

With this change, the main request-path lifecycle is now decomposed into explicit services for ingestion, normalization, features, registry, forecasting, signaling, and training. `CommodityService` remains as the stable facade for current routes, but it no longer owns the core implementation details for model lifecycle operations.

## Phase 8: Incremental implementation delivered in the reasoning slice

### What changes in this slice

- Rewire `app/services/ai_reasoning_engine.py` to use extracted services for modeled commodities:
  - ingestion
  - normalization
  - forecast
  - model registry
- Remove request-path dependence on `CommodityService` for modeled commodity live prices, historical series, forecast lookup, and regional momentum ranking
- Keep non-modeled commodities on the existing quote/trend fallback path

### Why this slice matters

The AI/chat path now consumes the staged architecture directly instead of rebuilding market context through the legacy facade. That reduces coupling between chat reasoning and backend orchestration and is the correct precursor to exposing richer structured signal and provenance contracts to the frontend and API consumers.

## Phase 9: Incremental implementation delivered in the durable training-job slice

### What changes in this slice

- Add:
  - `app/models/training_job.py`
  - `app/services/training_job_service.py`
- Persist training lifecycle state in a dedicated `training_jobs` table instead of process-local memory
- Create a queued job record in `/api/train/{commodity}/{region}` before background work starts
- Update background training to write explicit job transitions: `queued`, `processing`, `completed`, `failed`
- Keep `/api/train/{commodity}/{region}` returning `202 Accepted` with the existing response shape
- Update `/api/train/{commodity}/{region}/status` to read the latest persisted job state

### Why this slice matters

This removes the last major process-local coupling in the training path. Training status now survives application restarts, aligns with the extracted service boundaries, and gives the current polling API a durable source of truth without requiring a broader queueing rewrite.

## Phase 10: Incremental implementation delivered in the data-access and signal API slice

### What changes in this slice

- Add `app/services/signal_service.py`
- Extract signal scoring from `MarketSignalService` into a dedicated signal boundary
- Add dedicated APIs for separated data products:
  - `/api/normalized/live/{commodity}/{region}`
  - `/api/normalized/historical/{commodity}/{region}`
  - `/api/features/{commodity}/{region}`
  - `/api/forecasts/{commodity}/{region}`
  - `/api/signals/{commodity}/{region}`
- Keep existing `/api/live-prices`, `/api/historical`, `/api/predict`, and `/api/intelligence` routes working
- Add frontend client/types coverage for the new normalized, feature, forecast, and signal endpoints

### Why this slice matters

This is the first concrete API separation step toward the target architecture. Consumers can now request normalized market data, engineered features, forecasts, and signal products independently instead of only through facade-style endpoints or the bundled intelligence response.

## Phase 11: Incremental implementation delivered in the ingestion persistence slice

### What changes in this slice

- Add durable ingestion models:
  - `app/models/ingestion_job.py`
  - `app/models/raw_market_payload.py`
  - `app/models/normalized_market_record.py`
- Add `app/services/ingestion_persistence_service.py`
- Persist raw live/historical payload snapshots plus canonical normalized market records
- Add replay-safe normalized write behavior keyed by record type, commodity, region, period, and observed timestamp
- Add ingestion job tracking for queued/processing/completed/failed persistence workflows
- Add schema-guard coverage for ingestion indexes
- Route current live/historical and normalized/features endpoints through ingestion persistence while keeping response contracts unchanged

### Why this slice matters

This establishes the first durable ingestion and replay foundation in the current backend path. The system no longer depends exclusively on cache files and request-time reconstruction for market inputs, and future backfill, replay, and worker separation work now has explicit persistence targets to build on.

## Phase 12: Next phase for runtime separation and richer market datasets

### What remains from the target architecture

- First-class macro and news ingestion:
  - promote proxy-only macro features toward explicit macro feed ingestion
  - persist normalized news/headline records with deduplication instead of pull-on-demand summaries only
- Background runtime separation:
  - move beyond in-process FastAPI `BackgroundTasks` for long-running or replayable jobs
  - introduce queueable backfill/replay/training execution boundaries with durable job ownership
- Forecast lifecycle hardening:
  - add backtesting, promotion criteria, and model-performance tracking beyond latest-row registry lookup
  - create clearer registry metadata for production promotion and rollback decisions
- API and dashboard evolution:
  - keep current compatibility routes, but move consumers toward normalized/features/forecast/signal contracts
  - add caching around stable normalized snapshots and signal payloads
- Repository cleanup:
  - reduce ambiguity from legacy duplicate trees such as `backend/app` and `src`

### Proposed implementation focus for the next slice

The next practical slice should center on queued replay/backfill execution and persisted macro/news inputs.

1. Introduce durable replay/backfill workers over `ingestion_jobs` instead of in-process-only execution.
2. Add persisted macro dataset models and ingestion adapters.
3. Add persisted normalized news/headline tables with deduplication keys.
4. Extend feature materialization to read from persisted macro/news inputs instead of proxy-only request-time derivation.
5. Keep current APIs stable while expanding the persisted data foundation underneath them.

### Why this should be next

The highest remaining architectural gap is not request-path decomposition anymore; it is runtime ownership of ingestion and richer persisted inputs. Macro/news persistence and queueable replay execution are the prerequisites for reliable backfills, drift analysis, model governance, and fully separated worker processes.

## Phase 12: Incremental implementation delivered in the ingestion replay slice

### What changes in this slice

- Add `app/services/ingestion_replay_service.py`
- Extend `IngestionPersistenceService` with ingestion job lookup/status serialization and replay result accounting
- Add queueable historical backfill execution over persisted `ingestion_jobs`
- Add additive ingestion replay APIs:
  - `/api/ingestion/backfill/{commodity}/{region}`
  - `/api/ingestion/jobs/{job_id}`
- Add schema-guard coverage for ingestion job lookup indexing
- Add focused tests for ingestion replay job lifecycle, replay-safe persistence counts, and API wiring

### Why this slice matters

This is the first runtime-separation step for ingestion. Historical backfills are now represented as durable jobs and can be executed by job ID instead of only as request-time persistence side effects. The current API contracts remain intact while the backend gains a queue-friendly replay seam for future worker extraction and for the next persisted macro/news foundations.

## Phase 12: Incremental implementation delivered in the macro/news persistence slice

### What changes in this slice

- Add persisted macro and news foundation models:
  - `app/models/macro_metric_record.py`
  - `app/models/news_headline_record.py`
- Add:
  - `app/services/macro_persistence_service.py`
  - `app/services/news_persistence_service.py`
- Persist macro time series from the existing fetcher into first-class normalized records
- Persist commodity headlines with deterministic deduplication keys
- Extend `FeatureStoreService` so session-backed feature materialization reads persisted macro and news inputs instead of only request-time proxy derivation
- Keep current routes stable while wiring `/api/features`, training, forecasting, signal generation, and news summary through the persisted foundations when a session is available
- Add schema-guard coverage for macro/news dedupe and lookup indexes

### Why this slice matters

This closes the largest remaining Phase 12 data-foundation gap without a rewrite. Macro and news inputs now have durable storage and replay-safe deduplication, and feature generation can consume persisted contextual datasets under the existing APIs and service boundaries.
