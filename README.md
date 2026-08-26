# Research: JavaScript Test Smells Detection and Refactoring

A research project for detecting, analyzing, and refactoring test smells in JavaScript codebases using LLM-powered techniques.

## Table of Contents

- [Dissertation](#dissertation)
- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [Components](#components)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)

## Dissertation

This repository accompanies the master's dissertation that reports the study:

> **[Improving JavaScript Test Quality with Large Language Models: Lessons from Test
> Smell Refactoring](Masters_Dissertation.pdf)**
>
> Gabriel Amaral Sousa<br>
> Programa de Pós-Graduação em Ciência da Computação<br>
> Universidade Estadual de Feira de Santana — Feira de Santana, 2026

The full text (147 pages) is in the root of this repository as
[`Masters_Dissertation.pdf`](Masters_Dissertation.pdf).

## Overview

This research project provides a complete toolchain for:

- **Detecting** test smells in JavaScript/TypeScript projects using Steel and SNutsJS detectors
- **Analyzing** detected smells through an interactive web interface
- **Refactoring** test code using Large Language Models (LLMs)
- **Comparing** different LLM approaches and prompting strategies
- **Storing** results in a structured SQLite database for research analysis

## Features

### Test Smell Detection
- **Steel Detector**: Detects 10+ JavaScript test smells
- **SNutsJS Detector**: Additional test smell patterns
- Batch processing of multiple repositories
- Detailed smell reports with line numbers and context

### Interactive UI
- Web-based smell selector interface
- Filter by repository, smell type, and detection tool
- Code preview with syntax highlighting
- Annotation and note-taking capabilities
- Selection management for study planning

### LLM Refactoring Pipeline
- CLI interface for managing refactoring experiments
- Support for multiple LLM providers (Claude, GPT, Gemini)
- Different prompting strategies (zero-shot, chain-of-thought, few-shot)
- Automated testing and validation
- Experiment tracking and comparison

### Research Database
- Structured SQLite database schema
- Track detected smells, study selections, and experiments
- Export capabilities for data analysis
- Migration system for schema updates

## Quick Start

### 1. One-Command Installation

```bash
# Clone the repository
git clone <repository-url>
cd research-javascript-test-smells

# Run the unified installation script
./install.sh
```

The installation script will:
- ✓ Check prerequisites (Python 3.8+, Node.js 18+, npm)
- ✓ Create Python virtual environment
- ✓ Install all Python dependencies
- ✓ Install and compile Steel detector
- ✓ Install SNutsJS detector
- ✓ Install UI frontend and backend
- ✓ Set up SQLite database
- ✓ Run database migrations

### 2. Start the UI

```bash
# Activate Python environment
source .venv/bin/activate

# Start the Smell Selector UI
cd smell-selector-ui
./start.sh
```

The UI will be available at:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

### 3. Run Smell Detection

```bash
# Activate Python environment
source .venv/bin/activate

# Start the LLM Refactor Pipeline CLI
cd llm-refactor-pipeline
python -m llm_refactor

# In the CLI, analyze a repository
llm-refactor> /analyze-smells redux-offline

# Or analyze all repositories
llm-refactor> /analyze-smells all
```

## Installation

### Prerequisites

**Required:**
- Python 3.8 or higher
- Node.js 18 or higher
- npm (comes with Node.js)
- pip3 (comes with Python)

**Optional:**
- yarn (for faster package installation)
- git (for version control)

### Automated Installation (Recommended)

```bash
./install.sh
```

This single script handles all setup automatically. Check `install.log` if issues occur.

### Manual Installation

If you prefer manual installation or need to troubleshoot:

#### 1. Python Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install LLM Pipeline dependencies
pip install -r llm-refactor-pipeline/requirements.txt

# Install UI Backend dependencies
pip install -r smell-selector-ui/backend/requirements.txt
```

#### 2. Steel Detector

```bash
cd smell_detection_tools/steel
yarn install  # or npm install
yarn run compile  # or npm run compile
cd ../..
```

#### 3. SNutsJS Detector

```bash
cd smell_detection_tools/snutsjs
yarn install  # or npm install
cd ../..
```

#### 4. UI Frontend

```bash
cd smell-selector-ui/frontend
npm install
cd ../..
```

#### 5. Database Setup

```bash
cd smell-selector-ui/backend
python migrate_database.py
cd ../..
```

## Project Structure

```
research-javascript-test-smells/
├── README.md                       # This file
├── LICENSE                         # MIT (original research code)
├── THIRD_PARTY_NOTICES.md          # Licenses of vendored third-party code
├── Masters_Dissertation.pdf        # Full dissertation text
├── install.sh                      # Unified installation script
├── setup_venv.sh                   # Virtual environment setup
├── requirements.txt                # Python dependencies
│
├── docs/                           # Project documentation
│   ├── quickstart.md               # Getting started guide
│   ├── venv-setup.md               # Virtual environment guide
│   ├── running-tests.md            # How to run repository tests
│   ├── latex-documentation.md      # LaTeX/dissertation notes
│   ├── database/                   # Database guides (cleanup, export, migration)
│   └── history/                    # Historical implementation notes
│
├── scripts/                        # Research and maintenance scripts
│   ├── analysis/                   # Experiment analysis tools
│   ├── db/                         # Database inspection/maintenance
│   ├── manual_checks/              # Manual diagnostics (RunPod, TGI, parsing)
│   ├── archive/                    # One-off scripts kept for traceability
│   ├── check_smells.py             # Smell report checker
│   └── export_database.py          # Database export tool
│
├── llm-refactor-pipeline/          # Main refactoring pipeline (installable package)
│   ├── pyproject.toml              # Package definition (pip install -e)
│   ├── src/llm_refactor/           # Core CLI application
│   ├── docs/                       # Pipeline guides (+ docs/history/)
│   ├── scripts/                    # Operational tools
│   │   ├── migrations/             # Applied DB schema migrations
│   │   ├── backfills/              # Applied data backfills
│   │   └── archive/                # One-off debug scripts
│   └── requirements.txt            # Pipeline dependencies
│
├── smell_detection_tools/          # Test smell detectors
│   ├── steel/                      # Steel detector (TypeScript)
│   └── snutsjs/                    # SNutsJS detector (JavaScript)
│
├── smell-selector-ui/              # Web interface
│   ├── frontend/                   # React + Vite frontend
│   └── backend/                    # FastAPI backend
│
├── research_data/                  # Data storage (research.db)
├── repositories/                   # Study corpus (third-party projects)
├── smells_detected/                # Detection outputs per repository
├── tests_output/                   # Baseline test results per repository
└── batch_summaries/                # Batch experiment summaries
```

Path resolution note: Python scripts locate these data directories through
`llm_refactor.core.paths`, which anchors on the repository root (the directory
containing `repositories/`). This requires the pipeline package to be installed
in editable mode: `pip install -e llm-refactor-pipeline`.

## Usage

### Detecting Test Smells

#### Using the CLI

```bash
# Activate environment
source .venv/bin/activate

# Start CLI
cd llm-refactor-pipeline
python -m llm_refactor

# Available commands
llm-refactor> /status                           # Show project status
llm-refactor> /analyze-smells <repo-name>       # Analyze specific repo
llm-refactor> /analyze-smells all               # Analyze all repos
llm-refactor> /setup-repo <repo-name> <url>     # Add new repository
llm-refactor> /run-tests <repo-name>            # Run tests
llm-refactor> ui                                # Launch UI
llm-refactor> help                              # Show all commands
llm-refactor> exit                              # Exit CLI
```

#### Using Steel Directly

```bash
cd smell_detection_tools/steel
node dist/index.js --path ../../repositories/redux-offline --output report.json
```

#### Using SNutsJS Directly

```bash
cd smell_detection_tools/snutsjs
node export-csv-local.js
```

### Using the Web UI

#### 1. Start the UI

```bash
cd smell-selector-ui
./start.sh
```

#### 2. Open Browser

Navigate to http://localhost:5173

#### 3. Filter and Browse Smells

- Use dropdown filters for repository, smell type, and tool
- Click on a smell to view details and code context
- Add notes and annotations
- Mark smells for study

#### 4. Export Data

- Use the API endpoints to export selected smells
- Access CSV exports via the backend API

### Running Refactoring Experiments

```bash
# In the LLM Refactor Pipeline CLI
llm-refactor> /pipeline
```

This launches the refactoring experiment workflow where you can:
- Select smells to refactor
- Choose LLM provider and strategy
- Run experiments with different prompts
- Compare results and analyze success rates

## Components

### 1. LLM Refactor Pipeline

**Purpose**: CLI for managing the entire research workflow

**Key Features**:
- Repository management
- Smell detection orchestration
- Experiment execution
- Results analysis and comparison
- Database management

**Technologies**: Python, SQLAlchemy, Prompt Toolkit, Rich

### 2. Steel Detector

**Purpose**: Detect JavaScript test smells using AST analysis

**Detected Smells**:
- Assertion Roulette
- Duplicate Assert
- Magic Number
- Lazy Test
- Conditional Test Logic
- And more...

**Technologies**: TypeScript, Babel Parser, Babel Traverse

### 3. SNutsJS Detector

**Purpose**: Additional test smell detection with different patterns

**Technologies**: JavaScript, Babel Parser, Fastify (optional API)

### 4. Smell Selector UI

**Purpose**: Web interface for reviewing and selecting test smells

**Features**:
- Interactive smell browser
- Code viewer with syntax highlighting
- Filtering and search
- Annotation and note-taking
- Study smell selection

**Technologies**:
- **Frontend**: React 18, Vite, Prism.js, CSS Modules
- **Backend**: FastAPI, SQLAlchemy, Uvicorn

### 5. Research Database

**Purpose**: Store all detection results, selections, and experiments

**Schema**:
- `detected_smells`: All detected smells
- `study_smells`: Selected smells for study
- `smell_ui_metadata`: User annotations (with UNIQUE constraint on detected_smell_id)
- `experiments`: Refactoring attempts and results

**Technologies**: SQLite, SQLAlchemy ORM

**Database Access**: All components use **unified SQLAlchemy ORM** approach:
- Models defined in `llm-refactor-pipeline/src/llm_refactor/modules/database/models.py`
- CRUD operations in `llm-refactor-pipeline/src/llm_refactor/modules/database/crud.py`
- No raw SQL in application code (except complex analytics queries)
- Constraints and relationships managed by ORM
- Easy migration to PostgreSQL if needed

## Troubleshooting

### Installation Issues

**Problem**: `install.sh` fails

**Solution**:
```bash
# Check the log file
cat install.log

# Ensure prerequisites are met
python3 --version  # Should be 3.8+
node --version     # Should be 18+

# Try manual installation
source .venv/bin/activate
pip install -r llm-refactor-pipeline/requirements.txt
```

**Problem**: Permission denied when running `./install.sh`

**Solution**:
```bash
chmod +x install.sh
./install.sh
```

### UI Issues

**Problem**: UI doesn't start

**Solution**:
```bash
# Check if backend is running
curl http://localhost:8001/

# Check frontend
curl http://localhost:5173/

# View logs
cat /tmp/smell-selector-backend.log
cat /tmp/smell-selector-frontend.log

# Restart manually
cd smell-selector-ui/backend && python main.py
cd smell-selector-ui/frontend && npm run dev
```

**Problem**: No smells appear in UI

**Solution**:
```bash
# Check database
sqlite3 research_data/research.db "SELECT COUNT(*) FROM detected_smells;"

# If zero, run detection
cd llm-refactor-pipeline
python -m llm_refactor
# Then: /analyze-smells <repo-name>
```

### Detection Issues

**Problem**: Steel fails to compile

**Solution**:
```bash
cd smell_detection_tools/steel
rm -rf node_modules dist
yarn install
yarn run compile
```

**Problem**: SNutsJS errors

**Solution**:
```bash
cd smell_detection_tools/snutsjs
rm -rf node_modules
yarn install
```

### Database Issues

**Problem**: ON CONFLICT error when selecting smells

**Error**: `ON CONFLICT clause does not match any PRIMARY KEY or UNIQUE constraint`

**Solution**:
```bash
# Add missing UNIQUE constraint (keeps all data)
sqlite3 research_data/research.db
> CREATE UNIQUE INDEX IF NOT EXISTS uq_ui_metadata_smell
  ON smell_ui_metadata(detected_smell_id);
> .quit

# Verify the fix
sqlite3 research_data/research.db
> .schema smell_ui_metadata
> .quit
```

**Why this happens**: Older databases were created before the UNIQUE constraint was added to the `smell_ui_metadata` table. The constraint is required for proper upsert operations.

**Problem**: Database schema errors

**Solution**:
```bash
# Backup current database
cp research_data/research.db research_data/research.db.backup

# Re-run migrations
cd smell-selector-ui/backend
python migrate_database.py
```

**Problem**: Corrupt database

**Solution**:
```bash
# Restore from backup
cp research_data/research.db.backup research_data/research.db

# Or start fresh (WARNING: loses data)
rm research_data/research.db
cd smell-selector-ui/backend
python migrate_database.py
```

### Python Environment Issues

**Problem**: Module not found errors

**Solution**:
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Verify activation
which python  # Should show .venv/bin/python

# Reinstall packages
pip install -r llm-refactor-pipeline/requirements.txt
pip install -r smell-selector-ui/backend/requirements.txt
```

## API Documentation

Once the backend is running, visit:

**OpenAPI/Swagger Docs**: http://localhost:8001/docs

**Key Endpoints**:
- `GET /api/repositories` - List all repositories
- `GET /api/smells` - List detected smells (with filters)
- `GET /api/smells/{id}` - Get smell details
- `POST /api/smells/{id}/select` - Select smell for study
- `GET /api/study-smells` - List selected smells
- `GET /api/stats` - Database statistics
- `GET /api/export-selected-smells` - Export selections

## Contributing

This is an academic research project. To contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests if applicable
5. Submit a pull request

## License

The original research code in this repository is released under the
[MIT License](LICENSE).

This repository also vendors third-party projects that keep their own licenses — the
study corpus under `repositories/` and the detectors under `smell_detection_tools/`.
See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for details.

## Support

For issues or questions:

1. Check `install.log` for installation issues
2. Review this README's Troubleshooting section
3. Check component-specific documentation in subdirectories
4. Open an issue on the repository

## Acknowledgments

This project uses:
- **Steel**: JavaScript test smell detector
- **SNutsJS**: Alternative test smell detector
- **FastAPI**: Modern Python web framework
- **React**: Frontend UI library
- **SQLAlchemy**: Python SQL toolkit
- **Babel**: JavaScript AST parser

---

**Happy researching!** 🔬
