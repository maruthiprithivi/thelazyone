"""
Performance and Load Testing for MCP Server

Tests server performance, scalability, and resource usage.
"""

import pytest
import asyncio
import time
import psutil
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch, AsyncMock


class TestPerformance:
    """Performance and load testing suite."""
    
    @pytest.fixture
    def performance_config(self):
        """Performance testing configuration."""
        return {
            "concurrent_requests": 50,
            "duration_seconds": 60,
            "load_pattern": "ramp_up"
        }
    
    @pytest.mark.asyncio
    async def test_response_time_benchmarks(self):
        """Test response time benchmarks for all tools."""
        
        # Mock server setup
        with patch('src.mcp_server.llm.providers.OpenAIProvider') as mock_llm:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.generate_code.return_value = "def test(): return 'ok'"
            mock_llm_instance.analyze_code.return_value = "Analysis complete"
            mock_llm.return_value = mock_llm_instance
            
            from src.mcp_server.server import MCPServer
            from src.mcp_server.config import ServerConfig
            
            config = ServerConfig()
            config.debug = False  # Disable debug for performance testing
            server = MCPServer(config)
            await server.start()
            
            client = PerformanceTestClient(server)
            
            try:
                # Test tool response times
                tools_to_test = [
                    ("generate_code", {"prompt": "test", "language": "python"}),
                    ("debug_code", {"code": "test", "error": "test"}),
                    ("research_documentation", {"query": "test", "query_type": "general"})
                ]
                
                response_times = {}
                
                for tool_name, arguments in tools_to_test:
                    start_time = time.time()
                    result = await client.call_tool(tool_name, arguments)
                    end_time = time.time()
                    
                    response_time = end_time - start_time
                    response_times[tool_name] = response_time
                    
                    # Assert response time is under threshold
                    assert response_time < 5.0, f"{tool_name} took {response_time}s > 5s"
                
                # Print performance metrics
                print(f"Response times: {response_times}")
                
                # Ensure all tools are performant
                for tool, rt in response_times.items():
                    assert rt < 5.0, f"{tool} exceeds 5s threshold: {rt}s"
                
            finally:
                await server.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_request_handling(self):
        """Test concurrent request handling."""
        
        with patch('src.mcp_server.llm.providers.OpenAIProvider') as mock_llm:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.generate_code.return_value = "def test(): return 'concurrent'"
            mock_llm.return_value = mock_llm_instance
            
            from src.mcp_server.server import MCPServer
            from src.mcp_server.config import ServerConfig
            
            config = ServerConfig()
            server = MCPServer(config)
            await server.start()
            
            client = PerformanceTestClient(server)
            
            try:
                # Test concurrent requests
                concurrent_tasks = 25
                start_time = time.time()
                
                tasks = [
                    client.call_tool("generate_code", {
                        "prompt": f"test function {i}",
                        "language": "python"
                    })
                    for i in range(concurrent_tasks)
                ]
                
                results = await asyncio.gather(*tasks)
                end_time = time.time()
                
                total_time = end_time - start_time
                avg_time = total_time / concurrent_tasks
                
                # Assert concurrent processing
                assert len(results) == concurrent_tasks
                assert total_time < 10.0, f"Concurrent processing took {total_time}s > 10s"
                assert avg_time < 1.0, f"Average response time {avg_time}s > 1s"
                
                print(f"Concurrent {concurrent_tasks} requests in {total_time}s, avg: {avg_time}s")
                
            finally:
                await server.stop()
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self):
        """Test memory usage stability under load."""
        
        with patch('src.mcp_server.llm.providers.OpenAIProvider') as mock_llm:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.generate_code.return_value = "def test(): pass"
            mock_llm.return_value = mock_llm_instance
            
            from src.mcp_server.server import MCPServer
            from src.mcp_server.config import ServerConfig
            
            config = ServerConfig()
            server = MCPServer(config)
            await server.start()
            
            client = PerformanceTestClient(server)
            
            try:
                # Get initial memory usage
                process = psutil.Process()
                initial_memory = process.memory_info().rss / 1024 / 1024  # MB
                
                # Run multiple requests
                requests_count = 100
                for i in range(requests_count):
                    await client.call_tool("generate_code", {
                        "prompt": f"test {i}",
                        "language": "python"
                    })
                
                # Get final memory usage
                final_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = final_memory - initial_memory
                
                # Assert memory stability (increase < 50MB)
                assert memory_increase < 50, f"Memory increase {memory_increase}MB > 50MB"
                
                print(f"Memory usage: initial={initial_memory:.1f}MB, final={final_memory:.1f}MB, increase={memory_increase:.1f}MB")
                
            finally:
                await server.stop()
    
    @pytest.mark.asyncio
    async def test_load_testing(self):
        """Test server under sustained load."""
        
        with patch('src.mcp_server.llm.providers.OpenAIProvider') as mock_llm:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.generate_code.return_value = "def load_test(): return 'ok'"
            mock_llm.return_value = mock_llm_instance
            
            from src.mcp_server.server import MCPServer
            from src.mcp_server.config import ServerConfig
            
            config = ServerConfig()
            server = MCPServer(config)
            await server.start()
            
            client = PerformanceTestClient(server)
            
            try:
                # Load test parameters
                duration = 30  # seconds
                requests_per_second = 2
                total_requests = duration * requests_per_second
                
                start_time = time.time()
                successful_requests = 0
                failed_requests = 0
                response_times = []
                
                async def make_request(request_id):
                    nonlocal successful_requests, failed_requests
                    try:
                        request_start = time.time()
                        result = await client.call_tool("generate_code", {
                            "prompt": f"load test {request_id}",
                            "language": "python"
                        })
                        request_end = time.time()
                        
                        if result and "content" in result:
                            successful_requests += 1
                            response_times.append(request_end - request_start)
                        else:
                            failed_requests += 1
                    except Exception:
                        failed_requests += 1
                
                # Execute load test
                tasks = []
                for i in range(total_requests):
                    await asyncio.sleep(0.5)  # Rate limiting
                    tasks.append(make_request(i))
                
                await asyncio.gather(*tasks)
                
                end_time = time.time()
                actual_duration = end_time - start_time
                
                # Calculate metrics
                success_rate = (successful_requests / total_requests) * 100
                avg_response_time = sum(response_times) / len(response_times) if response_times else 0
                requests_per_second_actual = successful_requests / actual_duration
                
                # Assert load test criteria
                assert success_rate >= 95, f"Success rate {success_rate}% < 95%"
                assert avg_response_time < 2.0, f"Average response time {avg_response_time}s < 2s"
                assert requests_per_second_actual >= 1.5, f"RPS {requests_per_second_actual} < 1.5"
                
                print(f"Load test results:")
                print(f"  Total requests: {total_requests}")
                print(f"  Successful: {successful_requests} ({success_rate:.1f}%)")
                print(f"  Failed: {failed_requests}")
                print(f"  Duration: {actual_duration:.1f}s")
                print(f"  Avg response: {avg_response_time:.3f}s")
                print(f"  RPS: {requests_per_second_actual:.2f}")
                
            finally:
                await server.stop()
    
    @pytest.mark.asyncio
    async def test_rate_limiting_performance(self):
        """Test rate limiting under high load."""
        
        with patch('src.mcp_server.llm.providers.OpenAIProvider') as mock_llm:
            mock_llm_instance = AsyncMock()
            mock_llm_instance.generate_code.return_value = "def rate_limit_test(): return 'ok'"
            mock_llm.return_value = mock_llm_instance
            
            from src.mcp_server.server import MCPServer
            from src.mcp_server.config import ServerConfig
            
            config = ServerConfig()
            server = MCPServer(config)
            await server.start()
            
            client = PerformanceTestClient(server)
            
            try:
                # Test burst requests
                burst_size = 10
                burst_tasks = [
                    client.call_tool("generate_code", {
                        "prompt": f"burst {i}",
                        "language": "python"
                    })
                    for i in range(burst_size)
                ]
                
                start_time = time.time()
                results = await asyncio.gather(*burst_tasks, return_exceptions=True)
                end_time = time.time()
                
                # Should handle burst without failures
                successful = sum(1 for r in results if not isinstance(r, Exception))
                assert successful >= 8, f"Burst handling failed: {successful}/{burst_size}"
                
                burst_time = end_time - start_time
                assert burst_time < 3.0, f"Burst processing took {burst_time}s > 3s"
                
                print(f"Rate limiting burst test: {successful}/{burst_size} successful in {burst_time:.2f}s")
                
            finally:
                await server.stop()


class PerformanceTestClient:
    """Performance testing client."""
    
    def __init__(self, server):
        self.server = server
    
    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """Call tool with performance tracking."""
        request = {
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        return await self.server.handle_request(request)
    
    def get_memory_usage(self) -> dict:
        """Get current memory usage."""
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent()
        }