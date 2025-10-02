# Known Issues and Bug Tracker

## Financial Portfolio Automation System

**Last Updated:** October 2, 2025  
**System Version:** 1.0.0  
**Status:** Production Ready with Minor Issues

---

## 🚨 CRITICAL ISSUES (System Breaking)

*None currently identified*

---

## ⚠️ HIGH PRIORITY ISSUES (Functionality Impact)

### Issue #001: Strategy Backtesting CLI Command Failure
- **Status:** 🔴 Open
- **Severity:** High
- **Component:** CLI / Strategy Tools
- **Description:** CLI strategy backtest command fails with dependency injection error
- **Error:** `StrategyTools.__init__() missing 1 required positional argument: 'config'`
- **Impact:** Cannot run backtesting from CLI interface
- **Workaround:** Use direct Python scripts for backtesting
- **Files Affected:** 
  - `financial_portfolio_automation/cli/strategy_commands.py`
  - `financial_portfolio_automation/mcp/strategy_tools.py`
- **Assigned:** Unassigned
- **Created:** 2025-10-02
- **Last Updated:** 2025-10-02

---

## 🟡 MEDIUM PRIORITY ISSUES (User Experience Impact)

### Issue #002: Unicode Display Issues on Windows Console
- **Status:** 🔴 Open
- **Severity:** Medium
- **Component:** Console Output / Reporting
- **Description:** Unicode characters (emojis, special symbols) cause encoding errors on Windows cmd/PowerShell
- **Error:** `UnicodeEncodeError: 'charmap' codec can't encode character`
- **Impact:** Script crashes when displaying progress indicators and status symbols
- **Workaround:** Run scripts in environments with UTF-8 support (VS Code terminal, Windows Terminal)
- **Files Affected:**
  - `working_investment_system.py`
  - `stress_test_comprehensive.py`
  - Various reporting scripts
- **Assigned:** Unassigned
- **Created:** 2025-10-02
- **Last Updated:** 2025-10-02

### Issue #003: API Server Configuration Loading
- **Status:** 🔴 Open
- **Severity:** Medium
- **Component:** API Server / Configuration
- **Description:** API server fails to start without explicit environment variables set
- **Error:** `ConfigurationError: Alpaca API key and secret key are required`
- **Impact:** API server won't start in some environments
- **Workaround:** Set `PORTFOLIO_CONFIG_FILE` environment variable or provide credentials via env vars
- **Files Affected:**
  - `financial_portfolio_automation/api/app.py`
  - `financial_portfolio_automation/config/settings.py`
- **Assigned:** Unassigned
- **Created:** 2025-10-02
- **Last Updated:** 2025-10-02

### Issue #004: MCP Server Dependency Warnings
- **Status:** 🟡 Partial Fix Applied
- **Severity:** Medium
- **Component:** MCP Tools / Service Factory
- **Description:** MCP server shows multiple dependency injection warnings on startup
- **Error:** Various "not available" warnings for analytics, reporting, and strategy services
- **Impact:** Some MCP tools operate in demo mode instead of live data mode
- **Workaround:** Core MCP functionality works with graceful fallbacks
- **Files Affected:**
  - `financial_portfolio_automation/mcp/service_factory.py`
  - `financial_portfolio_automation/mcp/portfolio_tools.py`
  - Various MCP tool modules
- **Assigned:** Unassigned
- **Created:** 2025-10-02
- **Last Updated:** 2025-10-02
- **Notes:** Service factory created to improve dependency injection

---

## 🟢 LOW PRIORITY ISSUES (Cosmetic/Enhancement)

### Issue #005: bcrypt Version Warning
- **Status:** 🔴 Open
- **Severity:** Low
- **Component:** Dependencies / Authentication
- **Description:** bcrypt library shows version detection warning
- **Error:** `AttributeError: module 'bcrypt' has no attribute '__about__'`
- **Impact:** Cosmetic warning only, no functional impact
- **Workaround:** Ignore warning or update bcrypt dependency
- **Files Affected:** Third-party dependency
- **Assigned:** Unassigned
- **Created:** 2025-10-02
- **Last Updated:** 2025-10-02

### Issue #006: Pydantic Schema Deprecation Warning
- **Status:** 🔴 Open
- **Severity:** Low
- **Component:** API Schemas / Validation
- **Description:** Pydantic shows deprecation warning for schema configuration
- **Error:** `'schema_extra' has been renamed to 'json_schema_extra'`
- **Impact:** Cosmetic warning only, no functional impact
- **Workaround:** Update schema configurations to use new naming
- **Files Affected:** Various API schema files
- **Assigned:** Unassigned
- **Created:** 2025-10-02
- **Last Updated:** 2025-10-02

### Issue #007: Portfolio Analysis Empty Positions Error
- **Status:** 🔴 Open
- **Severity:** Low
- **Component:** Portfolio Analysis
- **Description:** Portfolio analysis script fails when no positions exist
- **Error:** `ValueError: max() iterable argument is empty`
- **Impact:** Analysis script crashes with empty portfolio
- **Workaround:** Ensure portfolio has positions before running analysis
- **Files Affected:** `portfolio_analysis.py`
- **Assigned:** Unassigned
- **Created:** 2025-10-02
- **Last Updated:** 2025-10-02

---

## ✅ RESOLVED ISSUES

### Issue #R001: MCP Portfolio Tools Async/Sync Mismatch
- **Status:** ✅ Resolved
- **Severity:** High
- **Component:** MCP Tools
- **Description:** Portfolio tools methods were async but called synchronously
- **Resolution:** Removed async/await from portfolio tool methods
- **Files Modified:**
  - `financial_portfolio_automation/mcp/portfolio_tools.py`
- **Resolved By:** System
- **Resolved Date:** 2025-10-02

### Issue #R002: Service Factory Dependency Injection
- **Status:** ✅ Resolved
- **Severity:** High
- **Component:** MCP Tools / Service Factory
- **Description:** Services couldn't be properly initialized due to missing dependency injection
- **Resolution:** Created comprehensive service factory with proper dependency management
- **Files Modified:**
  - `financial_portfolio_automation/mcp/service_factory.py`
  - `financial_portfolio_automation/mcp/portfolio_tools.py`
- **Resolved By:** System
- **Resolved Date:** 2025-10-02

### Issue #R003: Configuration Loading for Nested JSON
- **Status:** ✅ Resolved
- **Severity:** Medium
- **Component:** Configuration Management
- **Description:** Config manager couldn't handle nested JSON structure from config files
- **Resolution:** Updated config loading to handle both flat and nested configuration formats
- **Files Modified:**
  - `financial_portfolio_automation/config/settings.py`
- **Resolved By:** System
- **Resolved Date:** 2025-10-02

---

## 📋 ISSUE REPORTING TEMPLATE

When reporting new issues, please use this template:

```markdown
### Issue #XXX: [Brief Description]
- **Status:** 🔴 Open
- **Severity:** [Critical/High/Medium/Low]
- **Component:** [System Component]
- **Description:** [Detailed description of the issue]
- **Error:** [Error message if applicable]
- **Impact:** [How this affects system functionality]
- **Workaround:** [Temporary solution if available]
- **Files Affected:** [List of affected files]
- **Steps to Reproduce:**
  1. [Step 1]
  2. [Step 2]
  3. [Step 3]
- **Expected Behavior:** [What should happen]
- **Actual Behavior:** [What actually happens]
- **Environment:** [OS, Python version, etc.]
- **Assigned:** [Person working on it]
- **Created:** [Date]
- **Last Updated:** [Date]
```

---

## 🔧 DEBUGGING RESOURCES

### Common Troubleshooting Steps:
1. **Configuration Issues:** Check environment variables and config file paths
2. **Dependency Issues:** Verify all required packages are installed
3. **API Issues:** Confirm Alpaca credentials are valid and properly set
4. **Unicode Issues:** Use UTF-8 compatible terminal (Windows Terminal, VS Code)
5. **Port Conflicts:** Check for running processes on required ports

### Useful Debug Commands:
```bash
# Check system status
python final_system_verification.py

# Test MCP tools
python test_mcp_tools.py

# Check CLI functionality
python -m financial_portfolio_automation.cli.main health

# Run comprehensive tests
python stress_test_comprehensive.py
```

### Log Locations:
- **Application Logs:** `logs/portfolio_automation.log`
- **API Server Logs:** Console output when running uvicorn
- **MCP Server Logs:** Console output when running MCP server
- **CLI Logs:** Console output for CLI commands

---

## 📊 ISSUE STATISTICS

- **Total Issues:** 7 Open, 3 Resolved
- **Critical Issues:** 0
- **High Priority:** 1
- **Medium Priority:** 3
- **Low Priority:** 3
- **Resolution Rate:** 30%

---

## 🎯 NEXT STEPS

### Immediate Actions Needed:
1. Fix strategy backtesting CLI command dependency injection
2. Resolve Unicode encoding issues for Windows compatibility
3. Improve API server configuration loading

### Future Enhancements:
1. Implement comprehensive error handling for edge cases
2. Add automated testing for all identified scenarios
3. Create user-friendly error messages and recovery suggestions
4. Develop monitoring and alerting for production issues

---

**Note:** This document should be updated whenever new issues are discovered or existing issues are resolved. All team members should contribute to keeping this tracker current and accurate.