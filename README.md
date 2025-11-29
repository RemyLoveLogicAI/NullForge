# 🔥 AOL-CLI Fire Edition

**The Ultimate AI Coding Agent Command Line Interface**

A powerful, multi-agent CLI framework for executing complex programming and automation tasks using customizable LLM backends. Fire Edition is the advanced version of AOL-CLI with enhanced capabilities.

## ✨ Features

### 🤖 Multi-Agent System
- **Orchestrator Agent**: Coordinates complex tasks across specialized agents
- **Planner Agent**: Creates detailed, actionable execution plans
- **Coder Agent**: Expert code generation and modification
- **Researcher Agent**: Web search and documentation analysis
- **Reviewer Agent**: Code review and quality assurance
- **Debugger Agent**: Error analysis and fixing

### 🛠️ Advanced Tools
- **File Operations**: Read, write, edit, search with intelligent diffing
- **Shell Commands**: Full shell access with safety controls
- **Web Search**: DuckDuckGo integration for research
- **Code Analysis**: AST-based code understanding
- **Git Integration**: Status, diff, commit operations
- **Project Analysis**: Automatic technology detection

### 🎨 Beautiful TUI
- Rich terminal output with colors and formatting
- Progress indicators and live updates
- Syntax-highlighted code display
- Interactive mode with command history

### 🔌 Provider Support
- OpenAI (GPT-4, GPT-4o)
- Venice AI (Uncensored models)
- Ollama (Local models)
- Groq (Fast inference)
- Together AI
- OpenRouter
- Anthropic (Claude)
- Any OpenAI-compatible endpoint

## 🚀 Quick Start

### Installation

```bash
cd aol-cli-fire
pip install -e .

# Or with full features
pip install -e ".[full]"
```

### Basic Usage

```bash
# Set your API key
export OPENAI_API_KEY=your-key-here

# Run a task
fire run "Create a Python REST API with FastAPI"

# Use a preset
fire run "Build a React app" --preset venice

# Interactive mode
fire chat

# Analyze a project
fire analyze ./my-project
```

## 📋 Commands

### `fire run` - Execute a Goal

```bash
fire run "Your goal here" [OPTIONS]

Options:
  -p, --provider     LLM provider (openai, venice, ollama, etc.)
  --preset           Use a provider preset
  -m, --model        Model name
  -k, --api-key      API key
  -w, --workspace    Working directory
  -i, --max-iterations  Maximum iterations
  -v, --verbose      Verbose output
  -d, --debug        Debug mode
  --no-review        Disable code review
  --stream           Stream output
```

### `fire chat` - Interactive Mode

```bash
fire chat [OPTIONS]

Options:
  -p, --provider     LLM provider
  --preset           Provider preset
  -w, --workspace    Working directory
```

### `fire analyze` - Project Analysis

```bash
fire analyze [PATH] [OPTIONS]

Options:
  --deep    Perform deep analysis
```

### `fire config` - Configuration

```bash
fire config [OPTIONS]

Options:
  --preset NAME      Show preset configuration
  --list-presets     List all presets
  --show             Show current configuration
```

### `fire init` - Initialize Workspace

```bash
fire init [OPTIONS]

Options:
  -w, --workspace    Directory to initialize
```

## ⚙️ Configuration

### Environment Variables

```bash
# Provider
FIRE_LLM_PROVIDER=openai

# API Keys
OPENAI_API_KEY=sk-...
VENICE_API_KEY=...
GROQ_API_KEY=...

# Models
FIRE_ORCHESTRATOR_MODEL=gpt-4-turbo-preview
FIRE_CODER_MODEL=gpt-4-turbo-preview
FIRE_FAST_MODEL=gpt-3.5-turbo

# Behavior
FIRE_MAX_ITERATIONS=100
FIRE_ENABLE_CODE_REVIEW=true
FIRE_VERBOSE=false
```

### Presets

| Preset | Provider | Description |
|--------|----------|-------------|
| `openai` | OpenAI | GPT-4 Turbo |
| `openai-4o` | OpenAI | GPT-4o |
| `venice` | Venice AI | Llama 3.1 405B |
| `venice-uncensored` | Venice AI | Dolphin (uncensored) |
| `ollama` | Ollama | Local Llama 3.1 |
| `ollama-code` | Ollama | DeepSeek Coder |
| `groq` | Groq | Fast Llama 3.1 |
| `together` | Together AI | Llama 3.1 405B |
| `openrouter` | OpenRouter | Claude 3.5 Sonnet |
| `anthropic` | Anthropic | Claude 3.5 Sonnet |

## 🔥 Using Uncensored Models

### Venice AI

```bash
export VENICE_API_KEY=your-key
fire run "Your task" --preset venice-uncensored
```

### Ollama (Local)

```bash
# Pull an uncensored model
ollama pull dolphin-mixtral

# Use it
fire run "Your task" --provider ollama --model dolphin-mixtral
```

### Custom Endpoint

```bash
export CUSTOM_API_BASE=http://your-endpoint.com/v1
export CUSTOM_API_KEY=your-key
fire run "Your task" --provider custom --model your-model
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AOL-CLI Fire Edition                      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐     │
│  │Orchestr-│   │ Planner │   │  Coder  │   │Researcher│     │
│  │  ator   │──▶│  Agent  │──▶│  Agent  │──▶│  Agent  │     │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘     │
│       │                           │                          │
│       ▼                           ▼                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    Tool System                       │    │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐       │    │
│  │  │  File  │ │ Shell  │ │  Web   │ │  Git   │       │    │
│  │  │  Ops   │ │Commands│ │ Search │ │  Ops   │       │    │
│  │  └────────┘ └────────┘ └────────┘ └────────┘       │    │
│  └─────────────────────────────────────────────────────┘    │
│       │                                                      │
│       ▼                                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Memory & Context System                 │    │
│  │  • Conversation History  • Project Knowledge         │    │
│  │  • Semantic Memory       • Working Context          │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 📂 Project Structure

```
aol-cli-fire/
├── aol_fire/
│   ├── __init__.py          # Package exports
│   ├── core.py              # Configuration & main agent
│   ├── models.py            # Pydantic data models
│   ├── llm.py               # LLM wrapper
│   ├── workflow.py          # LangGraph workflow
│   ├── agents/              # Specialized agents
│   │   ├── orchestrator.py
│   │   ├── planner.py
│   │   ├── coder.py
│   │   └── prompts.py
│   ├── tools/               # Tool implementations
│   │   ├── file_tools.py
│   │   ├── shell_tools.py
│   │   ├── web_tools.py
│   │   ├── code_tools.py
│   │   ├── git_tools.py
│   │   └── project_tools.py
│   ├── memory/              # Memory system
│   ├── plugins/             # Plugin system
│   └── tui/                 # Terminal UI
├── tests/                   # Unit tests
├── main.py                  # CLI entry point
├── requirements.txt         # Dependencies
├── pyproject.toml           # Package config
└── README.md               # This file
```

## 🧪 Examples

### Create a Full-Stack App

```bash
fire run "Create a full-stack todo app with React frontend and FastAPI backend"
```

### Build a CLI Tool

```bash
fire run "Create a Python CLI for managing SSH connections with click"
```

### Add Tests

```bash
fire run "Add comprehensive unit tests for all modules in src/" --workspace ./myproject
```

### Code Refactoring

```bash
fire run "Refactor the authentication module to use JWT tokens" --workspace ./api
```

### Research and Implement

```bash
fire run "Research best practices for rate limiting and implement it in our API"
```

## 🔒 Safety

Fire Edition includes safety features that can be enabled/disabled:

- **Content Filtering**: Filter unsafe content (default: off)
- **Safety Checks**: Validate operations (default: off)
- **Command Blocking**: Block dangerous commands (configurable)
- **Confirmation Prompts**: Confirm destructive operations (default: off)

For unrestricted operation, all safety features are disabled by default.

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines.

## 📄 License

MIT License - see LICENSE for details.

---

**🔥 Fire Edition - Built for developers who want maximum power and flexibility.**
