"""
Test suite for Claude Code MCP Server

Comprehensive testing framework covering:
- Protocol compliance (MCP 2024-11-05)
- Functional integration tests
- End-to-end developer workflows
- Performance and load testing
- Security validation

Usage:
    # Run all tests
    ./scripts/run-e2e-tests.sh
    
    # Run specific test suites
    pytest tests/compliance/
    pytest tests/integration/
    pytest tests/e2e/
    pytest tests/performance/
    
    # Run with coverage
    pytest --cov=src --cov-report=html
"""

__version__ = "1.0.0"
__author__ = "Claude Code MCP Server Team"

# Test constants
TEST_SERVER_PORT = 8001
TEST_CONFIG_FILE = "test-config.yaml"
MOCK_LLM_RESPONSE = "def test_function(): return 'test'"
SUCCESS_THRESHOLD = 95  # Percentage
RESPONSE_TIME_THRESHOLD = 5  # Seconds
MEMORY_INCREASE_THRESHOLD = 50  # MB