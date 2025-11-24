# System Architecture (Draft)

## Components
- Web scraper
- NLP skill extraction pipeline
- Skill and job graph database
- Recommendation engine
- REST API (FastAPI)
- Frontend (React/Next.js)

## Data Flow
Job Boards → Scraper → Postgres → NLP Pipeline → Graph DB → Recommendation Engine → API → Frontend UI

## Tech Stack Justification
- FastAPI for async, production-grade APIs
- Neo4j for representing skill/job relationships
- Sentence-BERT for powerful vector embeddings
- React for dynamic UI + graph visualizations