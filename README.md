# The Lazy One 🤖

[![CI](https://github.com/maruthiprithivi/thelazyone/workflows/CI%20%26%20CD/badge.svg)](https://github.com/maruthiprithivi/thelazyone/actions)
[![PyPI version](https://badge.fury.io/py/thelazyone.svg)](https://badge.fury.io/py/thelazyone)
[![Python versions](https://img.shields.io/pypi/pyversions/thelazyone.svg)](https://pypi.org/project/thelazyone/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **AI-powered MCP server for automated code development with Claude Code integration**

## 🚀 Features

- **Multi-LLM Support**: OpenAI GPT-4 and Moonshot AI integration
- **Docker Containerization**: Secure code execution in isolated containers
- **MCP Protocol 2024**: Full Model Context Protocol compliance
- **Session Management**: State persistence and recovery
- **Real-time Research**: Context7 and web search integration
- **Comprehensive Logging**: Detailed journaling and debugging
- **Security First**: Rate limiting, input validation, and secure execution

## 📦 Installation

### From PyPI (Recommended)

```bash
pip install thelazyone
```

### From Source

```bash
git clone https://github.com/maruthiprithivi/thelazyone.git
cd thelazyone
pip install -e ".[dev]"
```

### Using Docker

```bash
docker pull ghcr.io/maruthiprithivi/thelazyone:latest
docker run -p 8000:8000 ghcr.io/maruthiprithivi/thelazyone:latest
```

## 🔧 Quick Start

### 1. Configuration

Create a `.env` file:

```bash
# Required API keys
OPENAI_API_KEY=your_openai_key_here
MOONSHOT_API_KEY=your_moonshot_key_here

# Optional configuration
MCP_SERVER_PORT=8000
MCP_DEBUG=true
MCP_STATE_DIRECTORY=./state
```

### 2. Start the Server

```bash
# Using CLI
thelazyone serve

# Using Docker
docker run -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  -e MOONSHOT_API_KEY=your_key \
  ghcr.io/maruthiprithivi/thelazyone:latest
```

### 3. Connect with Claude Code

Configure your IDE to connect to `http://localhost:8000` as the MCP endpoint.

## 🛠️ Usage Examples

### Code Generation

```python
# Using the MCP client
from mcp_client import MCPClient

client = MCPClient("http://localhost:8000")
response = await client.call_tool(
    "generate_code",
    {
        "requirements": "Create a REST API with FastAPI",
        "language": "python",
        "context": "Include authentication and database models"
    }
)
print(response["generated_code"])
```

### Session Management

```python
# Create a new session
session_id = await client.call_tool(
    "manage_session",
    {"action": "create", "context": {"project": "my-app"}}
)

# Update session
await client.call_tool(
    "manage_session",
    {"action": "update", "session_id": session_id, "context": {"new_feature": "auth"}}
)
```

### Research Documentation

```python
# Research best practices
results = await client.call_tool(
    "research_documentation",
    {
        "query": "Python async programming best practices",
        "query_type": "technical",
        "max_results": 5
    }
)
```

## 📋 Available Tools

| Tool | Description |
|------|-------------|
| `generate_code` | Generate code based on requirements |
| `debug_code` | Debug and fix code issues |
| `execute_tests` | Run tests in isolated containers |
| `research_documentation` | Research technical documentation |
| `create_requirements_spec` | Create project requirements |
| `create_design_spec` | Create software design documents |
| `manage_session` | Session state management |
| `setup_dev_environment` | Configure development environments |
| `execute_command` | Execute shell commands safely |

## 🔐 Security

- **Docker Isolation**: All code execution happens in containers
- **Rate Limiting**: Configurable request limits
- **Input Validation**: Comprehensive sanitization
- **API Key Security**: Environment variable based configuration
- **Audit Logging**: Complete operation tracking

## 🧪 Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/maruthiprithivi/thelazyone.git
cd thelazyone

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .
ruff format .

# Type checking
mypy src/
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=mcp_server --cov-report=html

# Run specific test file
pytest tests/test_comprehensive.py

# Run with specific Python version
tox -e py311
```

## 📊 Testing

The project includes comprehensive test suites:

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Load and stress testing
- **Security Tests**: Vulnerability scanning
- **Compliance Tests**: MCP protocol compliance

## 🔄 CI/CD

- **GitHub Actions**: Automated testing and deployment
- **Multi-platform**: Ubuntu, Windows, macOS
- **Multi-Python**: 3.11, 3.12, 3.13
- **PyPI Publishing**: Automated releases
- **Docker Images**: Containerized deployment

## 📈 Monitoring

### Health Check

```bash
# Check server health
curl http://localhost:8000/health

# Get server metrics
curl http://localhost:8000/metrics
```

### Logging

Logs are written to:
- Console (structured JSON)
- File (rotating logs)
- Journal (markdown format)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Contribution Steps

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Claude Code** team for the amazing AI assistant
- **Moonshot AI** for their powerful language models
- **OpenAI** for GPT-4 integration
- **MCP Protocol** contributors for the standardized interface

## 📞 Support

- **GitHub Issues**: [Report bugs and feature requests](https://github.com/maruthiprithivi/thelazyone/issues)
- **GitHub Discussions**: [Community support](https://github.com/maruthiprithivi/thelazyone/discussions)
- **Documentation**: [API Documentation](https://github.com/maruthiprithivi/thelazyone#api)

## 🏷️ Tags

`vibe-coding` `claude-code` `moonshot-ai` `mcp-server` `ai-assistant` `python-3.11` `python-3.12` `python-3.13` `pypi-package`

---

**Made with ❤️ by the Claude Code community**