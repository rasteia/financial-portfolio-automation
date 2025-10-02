#!/usr/bin/env python3
"""
System Health Check Script

Performs comprehensive health checks on all system components
including database, cache, API services, and external connections.
"""

import os
import sys
import asyncio
import logging
import time
import json
import psutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from financial_portfolio_automation.data.store import DataStore
from financial_portfolio_automation.data.cache import DataCache
from financial_portfolio_automation.config.settings import get_database_url, get_redis_url

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HealthChecker:
    """Comprehensive system health checker"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'UNKNOWN',
            'checks': {},
            'summary': {
                'total_checks': 0,
                'passed': 0,
                'failed': 0,
                'warnings': 0
            }
        }
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        logger.info("Starting comprehensive system health check...")
        
        checks = [
            ('system_resources', self.check_system_resources),
            ('database', self.check_database),
            ('cache', self.check_cache),
            ('api_services', self.check_api_services),
            ('external_connections', self.check_external_connections),
            ('file_system', self.check_file_system),
            ('configuration', self.check_configuration),
            ('security', self.check_security)
        ]
        
        for check_name, check_func in checks:
            try:
                logger.info(f"Running {check_name} check...")
                result = await check_func()
                self.results['checks'][check_name] = result
                self.update_summary(result)
            except Exception as e:
                logger.error(f"Error running {check_name} check: {e}")
                self.results['checks'][check_name] = {
                    'status': 'FAILED',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                self.results['summary']['failed'] += 1
            
            self.results['summary']['total_checks'] += 1
        
        # Determine overall status
        if self.results['summary']['failed'] > 0:
            self.results['overall_status'] = 'FAILED'
        elif self.results['summary']['warnings'] > 0:
            self.results['overall_status'] = 'WARNING'
        else:
            self.results['overall_status'] = 'HEALTHY'
        
        logger.info(f"Health check completed. Overall status: {self.results['overall_status']}")
        return self.results
    
    def update_summary(self, result: Dict[str, Any]):
        """Update summary statistics"""
        status = result.get('status', 'UNKNOWN')
        if status == 'HEALTHY':
            self.results['summary']['passed'] += 1
        elif status == 'WARNING':
            self.results['summary']['warnings'] += 1
        else:
            self.results['summary']['failed'] += 1
    
    async def check_system_resources(self) -> Dict[str, Any]:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024**3)
            
            # Load average (Unix-like systems)
            load_avg = None
            try:
                load_avg = os.getloadavg()
            except (OSError, AttributeError):
                pass  # Not available on Windows
            
            # Determine status
            status = 'HEALTHY'
            issues = []
            
            if cpu_percent > 90:
                status = 'WARNING'
                issues.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if memory_percent > 90:
                status = 'WARNING'
                issues.append(f"High memory usage: {memory_percent:.1f}%")
            
            if memory_available_gb < 0.5:
                status = 'FAILED'
                issues.append(f"Low available memory: {memory_available_gb:.2f}GB")
            
            if disk_percent > 90:
                status = 'WARNING'
                issues.append(f"High disk usage: {disk_percent:.1f}%")
            
            if disk_free_gb < 1.0:
                status = 'FAILED'
                issues.append(f"Low disk space: {disk_free_gb:.2f}GB free")
            
            return {
                'status': status,
                'issues': issues,
                'metrics': {
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'memory_available_gb': round(memory_available_gb, 2),
                    'disk_percent': round(disk_percent, 1),
                    'disk_free_gb': round(disk_free_gb, 2),
                    'load_average': load_avg
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def check_database(self) -> Dict[str, Any]:
        """Check database connectivity and health"""
        try:
            database_url = get_database_url()
            data_store = DataStore(database_url)
            
            start_time = time.time()
            
            # Test connection
            await data_store.initialize()
            
            # Test basic query
            result = await data_store._execute_query("SELECT 1 as test")
            if not result or result[0]['test'] != 1:
                raise Exception("Basic query failed")
            
            # Check table existence
            tables_result = await data_store._execute_query("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            
            table_count = len(tables_result)
            expected_tables = 12  # Expected number of tables
            
            # Test write operation
            test_timestamp = datetime.now()
            await data_store._execute_query("""
                INSERT INTO performance_metrics 
                (metric_type, metric_name, value, timestamp)
                VALUES ('health_check', 'database_test', 1.0, $1)
            """, test_timestamp)
            
            # Clean up test data
            await data_store._execute_query("""
                DELETE FROM performance_metrics 
                WHERE metric_type = 'health_check' AND metric_name = 'database_test'
            """)
            
            connection_time = time.time() - start_time
            
            await data_store.close()
            
            # Determine status
            status = 'HEALTHY'
            issues = []
            
            if connection_time > 5.0:
                status = 'WARNING'
                issues.append(f"Slow database connection: {connection_time:.2f}s")
            
            if table_count < expected_tables:
                status = 'WARNING'
                issues.append(f"Missing tables: expected {expected_tables}, found {table_count}")
            
            return {
                'status': status,
                'issues': issues,
                'metrics': {
                    'connection_time': round(connection_time, 3),
                    'table_count': table_count,
                    'expected_tables': expected_tables
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def check_cache(self) -> Dict[str, Any]:
        """Check cache (Redis) connectivity and health"""
        try:
            cache = DataCache()
            
            start_time = time.time()
            
            # Test basic operations
            test_key = f"health_check_{int(time.time())}"
            test_value = {"test": True, "timestamp": datetime.now().isoformat()}
            
            # Test set
            cache.set(test_key, test_value, ttl=60)
            
            # Test get
            retrieved_value = cache.get(test_key)
            if retrieved_value != test_value:
                raise Exception("Cache get/set test failed")
            
            # Test delete
            cache.delete(test_key)
            
            # Verify deletion
            deleted_value = cache.get(test_key)
            if deleted_value is not None:
                raise Exception("Cache delete test failed")
            
            operation_time = time.time() - start_time
            
            # Determine status
            status = 'HEALTHY'
            issues = []
            
            if operation_time > 1.0:
                status = 'WARNING'
                issues.append(f"Slow cache operations: {operation_time:.2f}s")
            
            return {
                'status': status,
                'issues': issues,
                'metrics': {
                    'operation_time': round(operation_time, 3)
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def check_api_services(self) -> Dict[str, Any]:
        """Check API services health"""
        try:
            import aiohttp
            
            # Check if API is running locally
            api_endpoints = [
                'http://localhost:8000/api/v1/system/health',
                'http://localhost:8000/api/v1/system/info'
            ]
            
            results = {}
            overall_status = 'HEALTHY'
            issues = []
            
            async with aiohttp.ClientSession() as session:
                for endpoint in api_endpoints:
                    try:
                        start_time = time.time()
                        async with session.get(endpoint, timeout=10) as response:
                            response_time = time.time() - start_time
                            
                            if response.status == 200:
                                data = await response.json()
                                results[endpoint] = {
                                    'status': 'HEALTHY',
                                    'response_time': round(response_time, 3),
                                    'data': data
                                }
                            else:
                                results[endpoint] = {
                                    'status': 'FAILED',
                                    'response_time': round(response_time, 3),
                                    'http_status': response.status
                                }
                                overall_status = 'FAILED'
                                issues.append(f"API endpoint {endpoint} returned {response.status}")
                    
                    except asyncio.TimeoutError:
                        results[endpoint] = {
                            'status': 'FAILED',
                            'error': 'Timeout'
                        }
                        overall_status = 'FAILED'
                        issues.append(f"API endpoint {endpoint} timed out")
                    
                    except Exception as e:
                        results[endpoint] = {
                            'status': 'FAILED',
                            'error': str(e)
                        }
                        overall_status = 'FAILED'
                        issues.append(f"API endpoint {endpoint} error: {str(e)}")
            
            return {
                'status': overall_status,
                'issues': issues,
                'endpoints': results,
                'timestamp': datetime.now().isoformat()
            }
            
        except ImportError:
            return {
                'status': 'WARNING',
                'issues': ['aiohttp not available for API testing'],
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def check_external_connections(self) -> Dict[str, Any]:
        """Check external service connections"""
        try:
            import aiohttp
            
            # Test external connections
            external_services = [
                ('Alpaca API', 'https://paper-api.alpaca.markets/v2/account'),
                ('Internet Connectivity', 'https://httpbin.org/get')
            ]
            
            results = {}
            overall_status = 'HEALTHY'
            issues = []
            
            async with aiohttp.ClientSession() as session:
                for service_name, url in external_services:
                    try:
                        start_time = time.time()
                        async with session.get(url, timeout=10) as response:
                            response_time = time.time() - start_time
                            
                            if response.status in [200, 401, 403]:  # 401/403 means service is reachable
                                results[service_name] = {
                                    'status': 'HEALTHY',
                                    'response_time': round(response_time, 3),
                                    'http_status': response.status
                                }
                            else:
                                results[service_name] = {
                                    'status': 'WARNING',
                                    'response_time': round(response_time, 3),
                                    'http_status': response.status
                                }
                                if overall_status == 'HEALTHY':
                                    overall_status = 'WARNING'
                                issues.append(f"{service_name} returned {response.status}")
                    
                    except asyncio.TimeoutError:
                        results[service_name] = {
                            'status': 'WARNING',
                            'error': 'Timeout'
                        }
                        if overall_status == 'HEALTHY':
                            overall_status = 'WARNING'
                        issues.append(f"{service_name} timed out")
                    
                    except Exception as e:
                        results[service_name] = {
                            'status': 'WARNING',
                            'error': str(e)
                        }
                        if overall_status == 'HEALTHY':
                            overall_status = 'WARNING'
                        issues.append(f"{service_name} error: {str(e)}")
            
            return {
                'status': overall_status,
                'issues': issues,
                'services': results,
                'timestamp': datetime.now().isoformat()
            }
            
        except ImportError:
            return {
                'status': 'WARNING',
                'issues': ['aiohttp not available for external connection testing'],
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def check_file_system(self) -> Dict[str, Any]:
        """Check file system health and permissions"""
        try:
            required_directories = [
                'data',
                'logs',
                'config',
                'reports',
                'backups'
            ]
            
            issues = []
            status = 'HEALTHY'
            directory_status = {}
            
            for directory in required_directories:
                dir_path = Path(directory)
                
                if not dir_path.exists():
                    directory_status[directory] = {
                        'exists': False,
                        'readable': False,
                        'writable': False
                    }
                    issues.append(f"Directory {directory} does not exist")
                    status = 'WARNING'
                else:
                    readable = os.access(dir_path, os.R_OK)
                    writable = os.access(dir_path, os.W_OK)
                    
                    directory_status[directory] = {
                        'exists': True,
                        'readable': readable,
                        'writable': writable
                    }
                    
                    if not readable:
                        issues.append(f"Directory {directory} is not readable")
                        status = 'FAILED'
                    
                    if not writable:
                        issues.append(f"Directory {directory} is not writable")
                        status = 'FAILED'
            
            # Test file operations
            test_file = Path('logs/health_check_test.txt')
            try:
                # Test write
                test_file.write_text(f"Health check test - {datetime.now().isoformat()}")
                
                # Test read
                content = test_file.read_text()
                
                # Test delete
                test_file.unlink()
                
                file_operations = {'write': True, 'read': True, 'delete': True}
            except Exception as e:
                file_operations = {'error': str(e)}
                issues.append(f"File operations test failed: {str(e)}")
                status = 'FAILED'
            
            return {
                'status': status,
                'issues': issues,
                'directories': directory_status,
                'file_operations': file_operations,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def check_configuration(self) -> Dict[str, Any]:
        """Check system configuration"""
        try:
            issues = []
            status = 'HEALTHY'
            config_status = {}
            
            # Check environment variables
            required_env_vars = [
                'DATABASE_URL',
                'REDIS_URL',
                'ALPACA_API_KEY',
                'ALPACA_SECRET_KEY'
            ]
            
            env_vars = {}
            for var in required_env_vars:
                value = os.getenv(var)
                env_vars[var] = {
                    'set': value is not None,
                    'empty': value == '' if value is not None else True
                }
                
                if not value:
                    issues.append(f"Environment variable {var} is not set")
                    status = 'WARNING'
                elif value in ['your_api_key_here', 'your_secret_key_here', 'change_me']:
                    issues.append(f"Environment variable {var} has default/placeholder value")
                    status = 'WARNING'
            
            config_status['environment_variables'] = env_vars
            
            # Check configuration files
            config_files = [
                'config/config.json',
                '.env'
            ]
            
            files_status = {}
            for config_file in config_files:
                file_path = Path(config_file)
                files_status[config_file] = {
                    'exists': file_path.exists(),
                    'readable': file_path.exists() and os.access(file_path, os.R_OK)
                }
                
                if not file_path.exists():
                    issues.append(f"Configuration file {config_file} does not exist")
                    status = 'WARNING'
                elif not os.access(file_path, os.R_OK):
                    issues.append(f"Configuration file {config_file} is not readable")
                    status = 'FAILED'
            
            config_status['configuration_files'] = files_status
            
            return {
                'status': status,
                'issues': issues,
                'configuration': config_status,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def check_security(self) -> Dict[str, Any]:
        """Check security-related configurations"""
        try:
            issues = []
            status = 'HEALTHY'
            security_status = {}
            
            # Check file permissions
            sensitive_files = [
                '.env',
                'config/ssl/server.key'
            ]
            
            file_permissions = {}
            for file_path in sensitive_files:
                path = Path(file_path)
                if path.exists():
                    stat_info = path.stat()
                    permissions = oct(stat_info.st_mode)[-3:]
                    
                    file_permissions[file_path] = {
                        'permissions': permissions,
                        'secure': permissions in ['600', '400']  # Only owner can read/write
                    }
                    
                    if permissions not in ['600', '400']:
                        issues.append(f"File {file_path} has insecure permissions: {permissions}")
                        status = 'WARNING'
                else:
                    file_permissions[file_path] = {
                        'exists': False
                    }
            
            security_status['file_permissions'] = file_permissions
            
            # Check for default passwords/keys
            env_file = Path('.env')
            if env_file.exists():
                content = env_file.read_text()
                default_values = [
                    'your_api_key_here',
                    'your_secret_key_here',
                    'change_me',
                    'password123',
                    'admin'
                ]
                
                found_defaults = []
                for default_val in default_values:
                    if default_val in content:
                        found_defaults.append(default_val)
                
                if found_defaults:
                    issues.append(f"Default values found in .env: {', '.join(found_defaults)}")
                    status = 'WARNING'
                
                security_status['default_values'] = {
                    'found': found_defaults,
                    'count': len(found_defaults)
                }
            
            return {
                'status': status,
                'issues': issues,
                'security': security_status,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


def format_results(results: Dict[str, Any], format_type: str = 'text') -> str:
    """Format health check results"""
    if format_type == 'json':
        return json.dumps(results, indent=2)
    
    # Text format
    output = []
    output.append("=" * 60)
    output.append("FINANCIAL PORTFOLIO AUTOMATION - HEALTH CHECK")
    output.append("=" * 60)
    output.append(f"Timestamp: {results['timestamp']}")
    output.append(f"Overall Status: {results['overall_status']}")
    output.append("")
    
    # Summary
    summary = results['summary']
    output.append("SUMMARY:")
    output.append(f"  Total Checks: {summary['total_checks']}")
    output.append(f"  Passed: {summary['passed']}")
    output.append(f"  Warnings: {summary['warnings']}")
    output.append(f"  Failed: {summary['failed']}")
    output.append("")
    
    # Individual checks
    for check_name, check_result in results['checks'].items():
        status = check_result.get('status', 'UNKNOWN')
        output.append(f"{check_name.upper().replace('_', ' ')}: {status}")
        
        if 'issues' in check_result and check_result['issues']:
            for issue in check_result['issues']:
                output.append(f"  - {issue}")
        
        if 'error' in check_result:
            output.append(f"  Error: {check_result['error']}")
        
        output.append("")
    
    return "\n".join(output)


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='System Health Check')
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Output format (default: text)')
    parser.add_argument('--output', help='Output file (default: stdout)')
    parser.add_argument('--quiet', action='store_true',
                       help='Only output errors and warnings')
    
    args = parser.parse_args()
    
    # Run health checks
    checker = HealthChecker()
    results = await checker.run_all_checks()
    
    # Format output
    formatted_output = format_results(results, args.format)
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            f.write(formatted_output)
        if not args.quiet:
            print(f"Health check results written to {args.output}")
    else:
        if not args.quiet or results['overall_status'] != 'HEALTHY':
            print(formatted_output)
    
    # Exit with appropriate code
    if results['overall_status'] == 'FAILED':
        return 1
    elif results['overall_status'] == 'WARNING':
        return 2 if not args.quiet else 0
    else:
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)