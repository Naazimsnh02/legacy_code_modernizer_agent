# 🤖 Legacy Code Modernizer - Autonomous AI Agent

[![Hugging Face Spaces](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Spaces-blue.svg)](https://huggingface.co/spaces)
[![Open in Spaces](https://img.shields.io/badge/Live%20Demo-Open%20in%20Spaces-brightgreen)](https://huggingface.co/spaces/MCP-1st-Birthday/legacy_code_modernizer)

**Track 2: MCP in Action - Enterprise Applications**

An autonomous AI agent that modernizes legacy codebases through intelligent planning, reasoning, and execution using Model Context Protocol (MCP) tools.

## 🎯 Project Overview

Legacy Code Modernizer is a complete autonomous agent system that transforms outdated code into modern, secure, and maintainable software. The agent autonomously:

1. **Plans** - Analyzes codebases and creates modernization strategies
2. **Reasons** - Makes intelligent decisions about transformation priorities
3. **Executes** - Applies transformations, generates tests, and validates changes
4. **Integrates** - Creates GitHub PRs with comprehensive documentation

## 🏆 Why This Project Stands Out

### Autonomous Agent Capabilities

**Multi-Phase Planning & Reasoning:**
- **Phase 1**: Intelligent file discovery and classification using AI pattern detection
- **Phase 2**: Semantic code analysis with vector-based similarity search (LlamaIndex + Chroma)
- **Phase 3**: Deep pattern analysis using multiple AI models (Gemini, Nebius AI)
- **Phase 4**: Autonomous code transformation with context-aware reasoning
- **Phase 5**: Automated testing in isolated sandbox + GitHub PR creation

**Context Engineering & RAG:**
- Vector embeddings for semantic code search
- Pattern grouping across similar files
- Historical transformation caching via MCP Memory
- Real-time migration guide retrieval via MCP Search

### MCP Tools Integration

The agent uses **4 MCP servers** as autonomous tools:

1. **GitHub MCP** - Autonomous PR creation with comprehensive documentation
2. **Tavily Search MCP** - Real-time migration guide discovery
3. **Memory MCP** - Pattern analysis caching and learning
4. **Filesystem MCP** - Safe file operations (planned)

### Real-World Enterprise Value

- **Multi-language support**: Python, Java, JavaScript, TypeScript
- **Secure execution**: Modal sandbox with isolated test environments
- **Production-ready**: Comprehensive test generation with coverage reporting

## 🚀 Demo

### Video Demo
**[Demo video](https://drive.google.com/file/d/1ph0NK8QKXRStjydqBV9w6HJaViirswE2/view?usp=sharing)**

### Social Media Post
**[Post on X](https://x.com/naazimhussain02/status/1994786125110710567?s=46&t=SdhRmvogISrVhMiZB_HDJQ)**

## 🎬 Quick Start

### Try It Live on Hugging Face Spaces

1. **Upload a code file** (Python, Java, JavaScript, TypeScript)
2. **Select target version** (auto-detected from your code)
3. **Click "Start Modernization"**
4. **Watch the autonomous agent work** through all 5 phases
5. **Download modernized code, tests, and reports**

### Local Installation

```bash
# Clone repository
git clone https://huggingface.co/spaces/MCP-1st-Birthday/legacy_code_modernizer_agent
cd legacy_code_modernizer_agent

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys:
# - GEMINI_API_KEY (required)
# - GITHUB_TOKEN (for PR creation)
# - TAVILY_API_KEY (for search)
# - MODAL_TOKEN_ID & MODAL_TOKEN_SECRET (for sandbox)

# Set up Python virtual environment
#   On macOS / Linux:
source venv/bin/activate
#   On Windows PowerShell:
.\venv\Scripts\Activate.ps1
#   On Windows CMD:
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Run the Gradio app
python app.py
```

## 🧠 Autonomous Agent Architecture

### Planning Phase
```
Input: Legacy codebase
↓
Agent analyzes file structure and content
↓
Classifies files by modernization priority
↓
Creates transformation roadmap
```

### Reasoning Phase
```
Agent groups similar patterns using vector search
↓
Retrieves migration guides via Tavily MCP
↓
Checks cached analyses via Memory MCP
↓
Prioritizes transformations by risk/impact
```

### Execution Phase
```
Agent transforms code with AI models
↓
Generates comprehensive test suites
↓
Validates in isolated Modal sandbox
↓
Auto-fixes export/import issues
```

### Integration Phase
```
Agent creates GitHub branch via GitHub MCP
↓
Commits transformed files
↓
Generates PR with deployment checklist
↓
Adds rollback plan and test results
```

## 🛠️ Technical Stack

### AI & LLM
- **Google Gemini** - Primary reasoning engine with large context window
- **Nebius AI** - Alternative model for diverse perspectives
- **LlamaIndex** - RAG framework for semantic code search
- **Chroma** - Vector database for embeddings
- **bge-large-en** - Embedding model deployed on Modal for inference

### MCP Integration
- **mcp** (v1.22.0) - Model Context Protocol SDK
- **@modelcontextprotocol/server-github** - GitHub operations
- **@modelcontextprotocol/server-tavily** - Web search
- **@modelcontextprotocol/server-memory** - Persistent storage

### Execution & Testing
- **Modal** - Serverless sandbox for secure test execution
- **pytest/Jest/JUnit** - Language-specific test frameworks
- **Coverage.py/JaCoCo** - Code coverage analysis

### UI & Orchestration
- **Gradio 6.0** - Interactive web interface
- **LangGraph** - Agent workflow orchestration
- **asyncio** - Asynchronous execution

## 📊 Features Showcase

### 1. Intelligent Pattern Detection
```python
# Agent automatically detects legacy patterns:
- Deprecated libraries (MySQLdb → PyMySQL)
- Security vulnerabilities (SQL injection)
- Python 2 syntax → Python 3
- Missing type hints
- Old-style string formatting
```

### 2. Semantic Code Search
```python
# Vector-based similarity search finds:
- Files with similar legacy patterns
- Related security vulnerabilities
- Common refactoring opportunities
```

### 3. Autonomous Test Generation
```python
# Agent generates:
- Unit tests with pytest/Jest/JUnit
- Integration tests
- Edge case coverage
- Performance benchmarks
```

### 4. GitHub Integration via MCP
```python
# Automated PR includes:
- Comprehensive change summary
- Test results with coverage
- Risk assessment
- Deployment checklist
- Rollback plan
```

## 🎯 Supported Languages & Versions

### Python
- **Versions**: 3.10, 3.11, 3.12, 3.13, 3.14
- **Frameworks**: Django 5.2 LTS, Flask 3.1, FastAPI 0.122
- **Testing**: pytest with coverage

### Java
- **Versions**: Java 17 LTS, 21 LTS, 23, 25 LTS
- **Frameworks**: Spring Boot 3.4, 4.0
- **Testing**: Maven + JUnit 5 + JaCoCo

### JavaScript
- **Standards**: ES2024, ES2025
- **Runtimes**: Node.js 22 LTS, 24 LTS, 25
- **Frameworks**: React 19, Angular 21, Vue 3.5, Express 5.1, Next.js 16
- **Testing**: Jest with coverage

### TypeScript
- **Versions**: 5.6, 5.7, 5.8, 5.9
- **Frameworks**: React 19, Angular 21, Next.js 16
- **Testing**: Jest with ts-jest

## 🔒 Security & Isolation

### Modal Sandbox Execution
- **Network isolation**: No external network access during tests
- **Filesystem isolation**: Temporary containers per execution
- **Resource limits**: CPU and memory constraints
- **Automatic cleanup**: Containers destroyed after execution

### Code Validation
- **Syntax checking**: Pre-execution validation
- **Import/export fixing**: Automatic resolution of module issues
- **Security scanning**: Detection of vulnerabilities
- **Type checking**: Language-specific validation


## 🎓 Advanced Features

### Context Engineering
- **Sliding window context**: Manages large files efficiently
- **Cross-file analysis**: Understands dependencies
- **Pattern learning**: Improves with usage via Memory MCP

### RAG Implementation
- **Semantic chunking**: Intelligent code splitting
- **Vector similarity**: Finds related patterns
- **Hybrid search**: Combines keyword + semantic search

### Agent Reasoning
- **Priority scoring**: Risk vs. impact analysis
- **Dependency tracking**: Understands file relationships

## 🙏 Acknowledgments

Built for **MCP's 1st Birthday Hackathon** hosted by Anthropic and Gradio.

**Powered by:**
- Google Gemini & Nebius AI
- Model Context Protocol (MCP)
- LlamaIndex & Chroma
- Modal
- Gradio

---

*Autonomous agents + MCP tools = The future of software development*
