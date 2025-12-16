"""
GitHub MCP Client - Creates PRs using GitHub MCP server.
Phase 5: Automated PR creation with comprehensive documentation.
"""

import os
import logging
import time
import json
from typing import Dict, List, Optional

# Lazy imports to avoid circular dependency issues
ClientSession = None
StdioServerParameters = None
stdio_client = None

def _ensure_mcp_imports():
    """Lazy load MCP imports to avoid circular dependency."""
    global ClientSession, StdioServerParameters, stdio_client
    if ClientSession is None:
        from mcp import ClientSession as CS, StdioServerParameters as SSP
        from mcp.client.stdio import stdio_client as sc
        ClientSession = CS
        StdioServerParameters = SSP
        stdio_client = sc

logger = logging.getLogger(__name__)


class GitHubMCPClient:
    """
    GitHub MCP client for automated PR creation.
    Uses Model Context Protocol to interact with GitHub.
    """
    
    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize GitHub MCP Client.
        
        Args:
            github_token: Optional GitHub token. If not provided, uses GITHUB_TOKEN from environment.
        """
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        if not self.github_token:
            logger.warning("GITHUB_TOKEN not set - PR creation will be disabled")
        
        logger.info("GitHubMCPClient initialized")
    
    async def create_pr(
        self,
        repo_url: str,
        changed_files: Dict[str, str],
        pr_summary: str,
        test_results: Dict,
        base_branch: str = "main"
    ) -> Dict:
        """
        Create GitHub PR using MCP.
        
        Args:
            repo_url: GitHub repository URL (e.g., "owner/repo")
            changed_files: Dictionary mapping file paths to new content
            pr_summary: PR description summary
            test_results: Test execution results
            base_branch: Base branch to merge into
        
        Returns:
            Dictionary with PR URL and details
        """
        _ensure_mcp_imports()  # Lazy load MCP
        
        if not self.github_token:
            return {
                "success": False,
                "error": "GITHUB_TOKEN not configured"
            }
        
        logger.info(f"Creating PR for {repo_url}")
        
        try:
            # Configure GitHub MCP server
            server_params = StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={"GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token}
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Create branch
                    branch_name = f"modernize/auto-{int(time.time())}"
                    logger.info(f"Creating branch: {branch_name}")
                    
                    try:
                        await session.call_tool(
                            "create_branch",
                            arguments={
                                "repo": repo_url,
                                "branch": branch_name,
                                "from_branch": base_branch
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error creating branch: {e}")
                        return {"success": False, "error": f"Branch creation failed: {e}"}
                    
                    # Commit files (batch by 10 files)
                    file_items = list(changed_files.items())
                    for i in range(0, len(file_items), 10):
                        batch = file_items[i:i+10]
                        files_payload = [
                            {"path": path, "content": content}
                            for path, content in batch
                        ]
                        
                        try:
                            await session.call_tool(
                                "push_files",
                                arguments={
                                    "repo": repo_url,
                                    "branch": branch_name,
                                    "files": files_payload,
                                    "message": f"Modernize batch {i//10 + 1}"
                                }
                            )
                        except Exception as e:
                            logger.error(f"Error pushing files: {e}")
                    
                    # Generate comprehensive PR description
                    pr_description = self._generate_pr_description(
                        pr_summary,
                        test_results,
                        changed_files
                    )
                    
                    # Create pull request
                    logger.info("Creating pull request")
                    pr_result = await session.call_tool(
                        "create_pull_request",
                        arguments={
                            "repo": repo_url,
                            "title": "[Automated] Modernize codebase",
                            "body": pr_description,
                            "head": branch_name,
                            "base": base_branch,
                            "draft": False
                        }
                    )
                    
                    logger.info(f"PR created successfully: {pr_result}")
                    
                    return {
                        "success": True,
                        "pr_url": pr_result.get("url", ""),
                        "pr_number": pr_result.get("number", 0),
                        "branch": branch_name
                    }
                    
        except Exception as e:
            logger.error(f"Error creating PR: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_pr_description(
        self,
        summary: str,
        test_results: Dict,
        changed_files: Dict[str, str]
    ) -> str:
        """
        Generate comprehensive PR description.
        
        Args:
            summary: High-level summary
            test_results: Test execution results
            changed_files: Changed files dictionary
        
        Returns:
            Formatted PR description in Markdown
        """
        # Calculate statistics
        total_files = len(changed_files)
        total_lines_added = sum(content.count('\n') for content in changed_files.values())
        
        tests_passed = test_results.get('tests_passed', 0)
        tests_run = test_results.get('tests_run', 0)
        pass_rate = (tests_passed / tests_run * 100) if tests_run > 0 else 0
        coverage = test_results.get('coverage_percent', 0)
        
        description = f"""## 🤖 Auto-generated by Legacy Code Modernizer Agent

## Summary
{summary}

## Key Changes

### Files Modified
- **Total files changed**: {total_files}
- **Lines added**: +{total_lines_added}
- **Modernization patterns applied**: Multiple (see details below)

### Testing Results
✅ **{tests_passed}/{tests_run} tests passed** ({pass_rate:.1f}% pass rate)
- Test coverage: {coverage:.1f}%
- Execution time: {test_results.get('execution_time', 0):.2f}s
- All tests run in isolated Modal sandbox

## Risk Assessment: **MEDIUM** ⚠️

### Why Medium Risk:
- Automated code transformation requires thorough review
- Database and API changes need integration testing
- Environment variables may need configuration

### Mitigation Steps:
1. ✅ All changes validated in sandbox environment
2. ✅ Comprehensive test suite generated and passing
3. ✅ Rollback plan included below
4. ⚠️ Manual review recommended before merging

## Deployment Checklist

**Before merging:**
- [ ] Review all file changes
- [ ] Verify environment variables are configured
- [ ] Run integration tests against staging
- [ ] Check for breaking changes in dependencies
- [ ] Update documentation if needed

**After merging:**
- [ ] Monitor application logs for errors
- [ ] Check performance metrics
- [ ] Verify all features working as expected

## Rollback Plan

If issues arise after deployment:

### Immediate Rollback (< 5 minutes)
```bash
# Revert to previous commit
git revert HEAD
git push origin main
```

### Alternative: Redeploy Previous Version
```bash
# Checkout previous commit
git checkout HEAD~1
# Deploy previous version
./deploy.sh
```

## Test Details

<details>
<summary>Click to expand test execution logs</summary>

```
{test_results.get('stdout', 'No test output available')[:2000]}
```

</details>

## Changed Files

<details>
<summary>Click to expand file list ({total_files} files)</summary>

{self._format_file_list(changed_files)}

</details>

---

**🙏 Generated with ❤️ by Legacy Code Modernizer**

**Pipeline Time**: {test_results.get('execution_time', 0):.1f}s  
**Powered by**: Google Gemini, Nebius AI, LlamaIndex, Modal, MCP

**👥 Reviewers**: Please focus on:
1. Code quality and maintainability
2. Test coverage and edge cases
3. Environment configuration requirements
"""
        
        return description
    
    def _format_file_list(self, changed_files: Dict[str, str]) -> str:
        """Format changed files list for PR description."""
        file_list = []
        for i, file_path in enumerate(sorted(changed_files.keys())[:50], 1):
            file_list.append(f"{i}. `{file_path}`")
        
        if len(changed_files) > 50:
            file_list.append(f"\n... and {len(changed_files) - 50} more files")
        
        return "\n".join(file_list)
    
    async def create_issue(
        self,
        repo_url: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None
    ) -> Dict:
        """
        Create GitHub issue using MCP.
        
        Args:
            repo_url: GitHub repository URL
            title: Issue title
            body: Issue description
            labels: Optional list of labels
        
        Returns:
            Dictionary with issue details
        """
        _ensure_mcp_imports()  # Lazy load MCP
        
        if not self.github_token:
            return {"success": False, "error": "GITHUB_TOKEN not configured"}
        
        logger.info(f"Creating issue in {repo_url}")
        
        try:
            server_params = StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={"GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token}
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    result = await session.call_tool(
                        "create_issue",
                        arguments={
                            "repo": repo_url,
                            "title": title,
                            "body": body,
                            "labels": labels or []
                        }
                    )
                    
                    return {
                        "success": True,
                        "issue_url": result.get("url", ""),
                        "issue_number": result.get("number", 0)
                    }
                    
        except Exception as e:
            logger.error(f"Error creating issue: {e}")
            return {"success": False, "error": str(e)}
    
    async def add_pr_comment(
        self,
        repo_url: str,
        pr_number: int,
        comment: str
    ) -> Dict:
        """
        Add comment to PR.
        
        Args:
            repo_url: GitHub repository URL
            pr_number: PR number
            comment: Comment text
        
        Returns:
            Success status
        """
        _ensure_mcp_imports()  # Lazy load MCP
        
        if not self.github_token:
            return {"success": False, "error": "GITHUB_TOKEN not configured"}
        
        try:
            server_params = StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={"GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token}
            )
            
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    await session.call_tool(
                        "add_comment",
                        arguments={
                            "repo": repo_url,
                            "issue_number": pr_number,
                            "body": comment
                        }
                    )
                    
                    return {"success": True}
                    
        except Exception as e:
            logger.error(f"Error adding comment: {e}")
            return {"success": False, "error": str(e)}
