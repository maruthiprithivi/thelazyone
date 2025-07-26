# Contributing to Claude Code MCP Server 🤝

Thank you for your interest in contributing to the Claude Code MCP Server! This document provides guidelines and information for contributors.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)
- [Getting Help](#getting-help)

## 🤝 Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- Docker (for containerized development)
- Git
- A text editor or IDE (VS Code, PyCharm, etc.)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:

```bash
git clone https://github.com/your-username/thelazyone.git
cd thelazyone
```

3. Add the upstream repository:

```bash
git remote add upstream https://github.com/maruthiprithivi/thelazyone.git
```

## 🔧 Development Setup

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### 2. Environment Variables

Create a `.env` file in the project root:

```bash
# Required API keys
OPENAI_API_KEY=your_openai_key_here
MOONSHOT_API_KEY=your_moonshot_key_here

# Optional configuration
MCP_SERVER_PORT=8000
MCP_DEBUG=true
MCP_STATE_DIRECTORY=./state
```

### 3. Docker Development (Optional)

```bash
# Build development Docker image
docker build -t claude-mcp-dev .

# Run with Docker Compose
docker-compose up
```

## 📝 Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/add-new-tool` - New features
- `fix/session-recovery` - Bug fixes
- `docs/update-readme` - Documentation updates
- `refactor/docker-setup` - Code refactoring
- `test/add-integration-tests` - Test improvements

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

Examples:
```
feat(llm): add Moonshot AI provider support
fix(docker): resolve container permission issues
docs(readme): update installation instructions
test(integration): add MCP protocol compliance tests
```

### Code Style

We use:
- **Ruff** for linting and formatting
- **Mypy** for type checking
- **Black** for code formatting (integrated with Ruff)

#### Running Code Quality Checks

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
mypy src/

# Run all checks
pre-commit run --all-files
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_comprehensive.py

# Run with coverage
pytest --cov=mcp_server --cov-report=html

# Run specific test class
pytest tests/test_comprehensive.py::TestServerStartup

# Run with verbose output
pytest -v

# Run tests with real API keys
OPENAI_API_KEY=your_key MOONSHOT_API_KEY=your_key pytest
```

### Test Types

- **Unit Tests**: `tests/` - Individual component testing
- **Integration Tests**: `tests/integration/` - End-to-end workflows
- **Performance Tests**: `tests/performance/` - Load and stress testing
- **Compliance Tests**: `tests/compliance/` - MCP protocol compliance

### Writing Tests

```python
import pytest
from mcp_server.server import MCPServer

@pytest.mark.asyncio
async def test_server_startup():
    """Test server startup and shutdown."""
    server = MCPServer()
    await server.start()
    assert server.is_running
    await server.stop()
```

## 🔄 Pull Request Process

### Before Creating PR

1. **Update your branch**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run all tests**:
   ```bash
   pytest
   ```

3. **Check code quality**:
   ```bash
   ruff check .
   mypy src/
   ```

### PR Requirements

- [ ] Tests pass locally
- [ ] Code is formatted and linted
- [ ] Documentation updated if needed
- [ ] CHANGELOG.md updated if applicable
- [ ] PR description is clear and complete
- [ ] Related issue is linked (if applicable)

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Performance improvement
- [ ] Other (please describe)

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing performed

## Documentation
- [ ] README updated
- [ ] API documentation updated
- [ ] Code comments added

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Tests pass locally
- [ ] No breaking changes (or documented)
```

## 🚀 Release Process

### Semantic Versioning

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Release Workflow

1. **Create release branch**:
   ```bash
   git checkout -b release/v1.2.0
   ```

2. **Update version** (if not using setuptools-scm):
   ```bash
   # Update pyproject.toml version
   # Update CHANGELOG.md
   ```

3. **Create PR to main**:
   ```bash
   git push origin release/v1.2.0
   # Create PR on GitHub
   ```

4. **Tag release** (after PR merge):
   ```bash
   git checkout main
   git tag v1.2.0
   git push origin v1.2.0
   ```

5. **GitHub Actions** will automatically:
   - Build and test
   - Publish to PyPI
   - Create GitHub release
   - Build Docker images

## 🐛 Debugging

### Common Issues

#### Docker Permission Issues
```bash
# Linux/macOS
sudo usermod -aG docker $USER
# Or use sudo for Docker commands
```

#### API Key Issues
```bash
# Verify API keys are set
echo $OPENAI_API_KEY
echo $MOONSHOT_API_KEY

# Test API connectivity
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

#### Test Failures
```bash
# Run tests with debug output
pytest -v --tb=short

# Run specific failing test
pytest tests/test_comprehensive.py::test_code_generation -v
```

## 🏗️ Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Client    │    │   MCP Server    │    │   LLM Provider  │
│                 │───▶│                 │───▶│  (OpenAI/      │
│   (IDE/CLI)     │◀───│   (FastAPI)     │◀───│   Moonshot)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   Docker        │
                       │   Containers    │
                       └─────────────────┘
```

### Components

- **MCP Server**: FastAPI-based web server
- **LLM Router**: Intelligent provider selection and load balancing
- **Docker Controller**: Container lifecycle management
- **Session Manager**: State persistence and recovery
- **Research Engine**: Context7 and web search integration
- **Journal Manager**: Comprehensive logging and debugging

## 📚 Documentation

- [API Documentation](docs/API.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [Development Setup](docs/DEVELOPMENT.md)
- [Architecture Guide](docs/ARCHITECTURE.md)
- [Examples](examples/)

## 🤝 Getting Help

### Support Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and community support
- **Discord**: [Join our community](https://discord.gg/claude-code-mcp)

### Before Asking for Help

1. Check the [FAQ](docs/FAQ.md)
2. Search existing [issues](https://github.com/maruthiprithivi/thelazyone/issues)
3. Review [troubleshooting guide](docs/TROUBLESHOOTING.md)

## 🎯 Roadmap

### Upcoming Features

- [ ] **Multi-language support**: JavaScript, TypeScript, Go, Rust
- [ ] **IDE Extensions**: VS Code, JetBrains plugins
- [ ] **Cloud deployment**: AWS, GCP, Azure templates
- [ ] **Team collaboration**: Shared sessions and workspaces
- [ ] **Performance optimization**: Caching and parallel processing
- [ ] **Advanced debugging**: Interactive debugging sessions

### Contributing to Roadmap

We welcome community input on our roadmap! Please:

1. Check existing [discussions](https://github.com/maruthiprithivi/thelazyone/discussions)
2. Create a new discussion for feature proposals
3. Vote on existing proposals with 👍 reactions

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Thank you for contributing to the Claude Code MCP Server!** 🚀

For questions or suggestions, please [open an issue](https://github.com/maruthiprithivi/thelazyone/issues/new) or start a [discussion](https://github.com/maruthiprithivi/thelazyone/discussions).