"""
Command Line Interface for Claude Code MCP Server

Provides command-line tools for starting, configuring, and managing the MCP server.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

from .server import MCPServer
from .config import load_config, ServerConfig


def create_parser() -> argparse.ArgumentParser:
    """Create the command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="claude-code-mcp-server",
        description="Claude Code MCP Server - Comprehensive coding assistance via MCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start                    # Start server with default config
  %(prog)s start -c config.yaml    # Start server with custom config
  %(prog)s validate -c config.yaml # Validate configuration file
  %(prog)s --version               # Show version information
        """
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )
    
    parser.add_argument(
        "-c", "--config",
        type=Path,
        help="Path to configuration file (YAML or JSON)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    start_parser = subparsers.add_parser(
        "start",
        help="Start the MCP server"
    )
    start_parser.add_argument(
        "--port",
        type=int,
        help="Server port (overrides config)"
    )
    start_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    
    # Validate command
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate configuration file"
    )
    
    # Config command
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration management"
    )
    config_subparsers = config_parser.add_subparsers(dest="config_action")
    
    config_subparsers.add_parser(
        "show",
        help="Show current configuration"
    )
    
    config_subparsers.add_parser(
        "example",
        help="Generate example configuration file"
    )
    
    return parser


async def start_server(args: argparse.Namespace) -> int:
    """Start the MCP server."""
    try:
        # Load configuration
        config = load_config(args.config)
        
        # Apply command line overrides
        if args.port:
            config.server_port = args.port
        if args.debug:
            config.debug = True
        if args.verbose:
            config.journal_settings.log_level = "DEBUG"
        
        # Create and start server
        server = MCPServer(config)
        await server.start()
        
        print(f"MCP Server started on port {config.server_port}")
        print("Press Ctrl+C to stop the server")
        
        # Keep server running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down server...")
        finally:
            await server.stop()
        
        return 0
        
    except Exception as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        return 1


def validate_config(args: argparse.Namespace) -> int:
    """Validate configuration file."""
    try:
        config = load_config(args.config)
        config.validate()
        print("Configuration is valid")
        return 0
        
    except Exception as e:
        print(f"Configuration validation failed: {e}", file=sys.stderr)
        return 1


def show_config(args: argparse.Namespace) -> int:
    """Show current configuration."""
    try:
        config = load_config(args.config)
        
        print("Current Configuration:")
        print("=" * 50)
        
        print(f"Default Model: {config.default_model}")
        print(f"Server Port: {config.server_port}")
        print(f"Debug Mode: {config.debug}")
        print(f"Spec Directory: {config.spec_directory}")
        
        print(f"\nLLM Providers ({len(config.llm_providers)}):")
        for i, provider in enumerate(config.llm_providers, 1):
            print(f"  {i}. {provider.provider.value} - {provider.model_name}")
        
        print(f"\nDocker Settings:")
        print(f"  Base Image: {config.docker_settings.base_image}")
        print(f"  Memory Limit: {config.docker_settings.memory_limit}")
        print(f"  CPU Limit: {config.docker_settings.cpu_limit}")
        print(f"  Timeout: {config.docker_settings.timeout}s")
        
        print(f"\nJournal Settings:")
        print(f"  Journal Path: {config.journal_settings.journal_path}")
        print(f"  Log Level: {config.journal_settings.log_level}")
        
        print(f"\nState Settings:")
        print(f"  State Directory: {config.state_settings.state_directory}")
        print(f"  Auto Recovery: {config.state_settings.auto_recovery}")
        
        return 0
        
    except Exception as e:
        print(f"Error showing configuration: {e}", file=sys.stderr)
        return 1


def generate_example_config(args: argparse.Namespace) -> int:
    """Generate example configuration file."""
    try:
        example_path = Path("config.example.yaml")
        if example_path.exists():
            print(f"Example configuration already exists at: {example_path}")
            return 0
        
        # Create default config and save as example
        config = ServerConfig()
        config.save(example_path, format="yaml")
        
        print(f"Example configuration generated at: {example_path}")
        print("Copy this file to config.yaml and customize for your environment")
        
        return 0
        
    except Exception as e:
        print(f"Error generating example configuration: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        if args.command == "start":
            return asyncio.run(start_server(args))
        elif args.command == "validate":
            return validate_config(args)
        elif args.command == "config":
            if args.config_action == "show":
                return show_config(args)
            elif args.config_action == "example":
                return generate_example_config(args)
            else:
                parser.print_help()
                return 1
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())