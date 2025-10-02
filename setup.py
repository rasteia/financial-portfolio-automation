"""Setup configuration for Financial Portfolio Automation Framework."""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="financial-portfolio-automation",
    version="0.1.0",
    author="Portfolio Automation Team",
    author_email="team@portfolioautomation.com",
    description="Intelligent financial analysis automation framework with Alpaca Markets integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/financial-portfolio-automation",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Scientific/Engineering :: Information Analysis",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "pytest-mock>=3.11.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
            "pre-commit>=3.3.0",
        ],
        "postgres": ["psycopg2-binary>=2.9.0"],
        "redis": ["redis>=4.5.0"],
        "notifications": ["twilio>=8.5.0"],
    },
    entry_points={
        "console_scripts": [
            "portfolio-automation=financial_portfolio_automation.cli.main:main",
            "portfolio-cli=financial_portfolio_automation.cli.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "financial_portfolio_automation": [
            "config/*.yaml",
            "config/*.json",
        ],
    },
)