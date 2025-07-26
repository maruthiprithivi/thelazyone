#!/bin/bash
# Claude Code MCP Server - End-to-End Automated Testing Script

set -e  # Exit on any error

echo "🧪 Claude Code MCP Server - End-to-End Testing"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test configuration
TEST_DURATION=60
CONCURRENT_REQUESTS=25
SUCCESS_THRESHOLD=95

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
echo "📋 Checking prerequisites..."

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_status "Python found: $PYTHON_VERSION"
else
    print_error "Python3 not found. Please install Python 3.9+"
    exit 1
fi

# Check Docker
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        print_status "Docker is running"
    else
        print_warning "Docker found but not running. Starting Docker..."
        # Try to start Docker on different systems
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            sudo systemctl start docker
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            open --background -a Docker
            sleep 10
        fi
        
        if ! docker info &> /dev/null; then
            print_error "Failed to start Docker. Please start Docker manually."
            exit 1
        fi
    fi
else
    print_error "Docker not found. Please install Docker."
    exit 1
fi

# Setup test environment
echo "🔧 Setting up test environment..."

# Create test directory
TEST_DIR="$(pwd)/test-results"
mkdir -p "$TEST_DIR"
mkdir -p "$TEST_DIR/protocol"
mkdir -p "$TEST_DIR/integration"
mkdir -p "$TEST_DIR/e2e"
mkdir -p "$TEST_DIR/performance"

# Install test dependencies
if [ ! -f requirements-test.txt ]; then
    cat > requirements-test.txt << EOF
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-xdist>=3.3.0
psutil>=5.9.0
asyncio-mqtt>=0.16.0
EOF
fi

print_status "Installing test dependencies..."
pip install -r requirements-test.txt

# Create test configuration
echo "⚙️  Creating test configuration..."

TEST_CONFIG_FILE="$TEST_DIR/test-config.yaml"
cat > "$TEST_CONFIG_FILE" << EOF
# Test configuration for MCP server
llm_providers:
  - provider: "openai"
    api_key: "test-key"
    model_name: "gpt-3.5-turbo"
    max_tokens: 1000
    temperature: 0.1

docker_settings:
  base_image: "python:3.11-slim"
  memory_limit: "256m"
  cpu_limit: "0.5"
  timeout: 30

research_settings:
  context7_enabled: false  # Mock for testing
  web_search_enabled: false  # Mock for testing
  cache_ttl: 300
  max_results: 3

journal_settings:
  journal_path: "$TEST_DIR/test-journal.md"
  log_level: "INFO"
  max_entries: 1000

state_settings:
  state_directory: "$TEST_DIR/state"
  checkpoint_interval: 60
  max_checkpoints: 10
  auto_recovery: true

spec_directory: "$TEST_DIR/specs"
server_port: 8001
debug: true
EOF

# Function to wait for server to be ready
wait_for_server() {
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for MCP server to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8001/health > /dev/null 2>&1; then
            print_status "MCP server is ready"
            return 0
        fi
        echo "  Attempt $attempt/$max_attempts..."
        sleep 2
        ((attempt++))
    done
    
    print_error "MCP server failed to start within $max_attempts attempts"
    return 1
}

# Function to run tests with progress tracking
run_test_suite() {
    local suite_name=$1
    local test_path=$2
    local output_dir=$3
    
    echo ""
    echo "🔍 Running $suite_name tests..."
    echo "--------------------------------"
    
    local start_time=$(date +%s)
    
    # Run tests with coverage
    if pytest "$test_path" \
        --verbose \
        --tb=short \
        --cov=src \
        --cov-report=html:"$output_dir/coverage" \
        --cov-report=xml:"$output_dir/coverage.xml" \
        --junit-xml="$output_dir/results.xml" \
        --html="$output_dir/report.html" \
        --self-contained-html \
        2> "$output_dir/errors.log"; then
        
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        
        print_status "$suite_name tests completed in ${duration}s"
        return 0
    else
        print_error "$suite_name tests failed"
        return 1
    fi
}

# Start MCP server for testing
echo "🚀 Starting MCP server for testing..."

# Start server in background
python -m src.mcp_server.cli start -c "$TEST_CONFIG_FILE" > "$TEST_DIR/server.log" 2>&1 &
SERVER_PID=$!

# Wait for server to be ready
if ! wait_for_server; then
    print_error "Failed to start MCP server"
    cat "$TEST_DIR/server.log"
    exit 1
fi

# Run tests in sequence
echo ""
echo "🧪 Starting comprehensive testing..."
echo "============================="

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Phase 1: Protocol Compliance Tests
print_status "Phase 1: Protocol Compliance Tests"
if run_test_suite "Protocol Compliance" "tests/compliance" "$TEST_DIR/protocol"; then
    ((PASSED_TESTS++))
else
    ((FAILED_TESTS++))
fi
((TOTAL_TESTS++))

# Phase 2: Functional Integration Tests
print_status "Phase 2: Functional Integration Tests"
if run_test_suite "Integration" "tests/integration" "$TEST_DIR/integration"; then
    ((PASSED_TESTS++))
else
    ((FAILED_TESTS++))
fi
((TOTAL_TESTS++))

# Phase 3: End-to-End Workflow Tests
print_status "Phase 3: End-to-End Workflow Tests"
if run_test_suite "End-to-End" "tests/e2e" "$TEST_DIR/e2e"; then
    ((PASSED_TESTS++))
else
    ((FAILED_TESTS++))
fi
((TOTAL_TESTS++))

# Phase 4: Performance Tests
print_status "Phase 4: Performance Tests"
if run_test_suite "Performance" "tests/performance" "$TEST_DIR/performance"; then
    ((PASSED_TESTS++))
else
    ((FAILED_TESTS++))
fi
((TOTAL_TESTS++))

# Stop server
print_status "Stopping MCP server..."
kill $SERVER_PID 2>/dev/null || true
sleep 2

# Generate comprehensive test report
echo ""
echo "📊 Generating comprehensive test report..."
echo "====================================="

# Create HTML report
cat > "$TEST_DIR/index.html" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>Claude Code MCP Server - Test Results</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .success { color: green; }
        .failure { color: red; }
        .summary { background: #f5f5f5; padding: 20px; border-radius: 5px; }
        .phase { margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Claude Code MCP Server - Test Results</h1>
    
    <div class="summary">
        <h2>Test Summary</h2>
        <p><strong>Total Tests:</strong> $TOTAL_TESTS</p>
        <p><strong class="success">Passed:</strong> $PASSED_TESTS</p>
        <p><strong class="failure">Failed:</strong> $FAILED_TESTS</p>
        <p><strong>Success Rate:</strong> $(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc)%</p>
    </div>
    
    <div class="phase">
        <h3>Test Phases</h3>
        <ul>
            <li><a href="protocol/report.html">Protocol Compliance Tests</a></li>
            <li><a href="integration/report.html">Functional Integration Tests</a></li>
            <li><a href="e2e/report.html">End-to-End Workflow Tests</a></li>
            <li><a href="performance/report.html">Performance Tests</a></li>
        </ul>
    </div>
    
    <div class="phase">
        <h3>Test Reports</h3>
        <ul>
            <li><a href="protocol/coverage/index.html">Code Coverage Report</a></li>
            <li><a href="protocol/results.xml">JUnit XML Results</a></li>
            <li><a href="server.log">Server Logs</a></li>
        </ul>
    </div>
</body>
</html>
EOF

# Summary report
echo ""
echo "🎯 Test Execution Complete"
echo "=========================="
echo "📊 Summary:"
echo "  Total Test Suites: $TOTAL_TESTS"
echo "  Passed: $PASSED_TESTS"
echo "  Failed: $FAILED_TESTS"
echo "  Success Rate: $(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc)%"
echo ""
echo "📁 Test Results Location: $TEST_DIR"
echo "  📊 HTML Report: $TEST_DIR/index.html"
echo "  📈 Coverage: $TEST_DIR/protocol/coverage/index.html"
echo "  📝 Server Logs: $TEST_DIR/server.log"
echo ""

# Final status
if [ $FAILED_TESTS -eq 0 ]; then
    print_status "🎉 All tests passed! MCP server is production-ready."
    exit 0
else
    print_error "❌ Some tests failed. Please review the reports."
    exit 1
fi