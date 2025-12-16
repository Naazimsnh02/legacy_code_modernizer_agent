"""Gradio UI for Legacy Code Modernizer Agent - Phase 5 Complete."""

import gradio as gr
import os
import asyncio
import logging
import zipfile
import tempfile
from dotenv import load_dotenv
from pathlib import Path

# Import orchestrator
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.workflow.orchestrator import ModernizationOrchestrator

# Load environment variables
load_dotenv()

# Configure logging with sensitive data redaction
class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive information from logs."""
    def __init__(self):
        super().__init__()
        self.sensitive_patterns = []
        
        # Collect sensitive values from environment
        sensitive_keys = [
            "GEMINI_API_KEY", 
            "NEBIUS_API_KEY", 
            "OPENAI_API_KEY", 
            "MODAL_TOKEN_ID", 
            "MODAL_TOKEN_SECRET",
            "GITHUB_TOKEN"
        ]
        
        for key in sensitive_keys:
            value = os.getenv(key)
            if value and len(value) > 5:  # Only redact if value is substantial
                self.sensitive_patterns.append(value)

    def filter(self, record):
        msg = str(record.msg)
        for sensitive_value in self.sensitive_patterns:
            if sensitive_value in msg:
                msg = msg.replace(sensitive_value, "[REDACTED]")
        record.msg = msg
        return True

# Initialize logging with redaction
logging.basicConfig(level=logging.INFO)
root_logger = logging.getLogger()
root_logger.addFilter(SensitiveDataFilter())
logger = logging.getLogger(__name__)

# Initialize orchestrator with intelligent pattern matching
orchestrator = ModernizationOrchestrator(use_intelligent_matcher=True)


# Supported file extensions for single file upload
SUPPORTED_EXTENSIONS = {
    # Python
    '.py', '.pyw', '.pyx',
    # Java
    '.java',
    # JavaScript/TypeScript
    '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'
}

# Language to file extension mapping
LANGUAGE_EXTENSIONS = {
    'python': ['.py', '.pyw', '.pyx'],
    'java': ['.java'],
    'javascript': ['.js', '.jsx', '.mjs', '.cjs'],
    'typescript': ['.ts', '.tsx']
}

# Target version options for each language (Updated November 2025)
TARGET_VERSIONS = {
    'python': ['Python 3.14', 'Python 3.13', 'Python 3.12', 'Python 3.11', 'Python 3.10'],
    'java': ['Java 25 LTS', 'Java 23', 'Java 21 LTS', 'Java 17 LTS'],
    'javascript': ['ES2025', 'ES2024', 'Node.js 25', 'Node.js 24 LTS', 'Node.js 22 LTS'],
    'typescript': ['TypeScript 5.9', 'TypeScript 5.8', 'TypeScript 5.7', 'TypeScript 5.6']
}

# Framework-specific versions (Updated November 2025)
FRAMEWORK_VERSIONS = [
    'React 19', 'React 18', 'React 18 (Hooks)', 'React 17',
    'Angular 21', 'Angular 20', 'Angular 19',
    'Vue 3.5', 'Vue 3.4', 'Vue 2.7',
    'Django 5.2 LTS', 'Django 5.1', 'Django 5.0',
    'Flask 3.1', 'Flask 3.0', 'Flask 2.3',
    'Spring Boot 4.0', 'Spring Boot 3.4', 'Spring Boot 3.3',
    'Laravel 12', 'Laravel 11',
    'Rails 8.1', 'Rails 8.0', 'Rails 7.2',
    'Express 5.1', 'Express 5.0', 'Express 4.21',
    'FastAPI 0.122', 'FastAPI 0.115',
    'Next.js 16', 'Next.js 15', 'Next.js 14'
]

def detect_language_from_extension(file_ext):
    """Detect language from file extension."""
    for lang, exts in LANGUAGE_EXTENSIONS.items():
        if file_ext in exts:
            return lang
    return None


def get_target_versions_for_language(language):
    """Get appropriate target versions for a detected language."""
    if not language:
        # Return all options if language unknown
        all_versions = []
        for versions in TARGET_VERSIONS.values():
            all_versions.extend(versions)
        all_versions.extend(FRAMEWORK_VERSIONS)
        return sorted(set(all_versions))
    
    # Get language-specific versions
    versions = TARGET_VERSIONS.get(language, [])
    
    # Add framework versions for web languages
    if language in ['javascript', 'typescript']:
        versions.extend([v for v in FRAMEWORK_VERSIONS if 'React' in v or 'Angular' in v or 'Vue' in v or 'Express' in v])
    elif language == 'python':
        versions.extend([v for v in FRAMEWORK_VERSIONS if 'Django' in v or 'Flask' in v or 'FastAPI' in v])
    elif language == 'java':
        versions.extend([v for v in FRAMEWORK_VERSIONS if 'Spring' in v])
    elif language == 'php':
        versions.extend([v for v in FRAMEWORK_VERSIONS if 'Laravel' in v])
    elif language == 'ruby':
        versions.extend([v for v in FRAMEWORK_VERSIONS if 'Rails' in v])
    
    return versions if versions else get_target_versions_for_language(None)


def detect_languages_from_files(file_paths):
    """
    Detect languages from multiple files.
    
    Args:
        file_paths: List of file paths
        
    Returns:
        Dictionary with language counts and suggested target versions
    """
    language_counts = {}
    
    for file_path in file_paths:
        ext = Path(file_path).suffix.lower()
        lang = detect_language_from_extension(ext)
        if lang:
            language_counts[lang] = language_counts.get(lang, 0) + 1
    
    if not language_counts:
        return None, []
    
    # Get primary language (most files)
    primary_language = max(language_counts.items(), key=lambda x: x[1])[0]
    
    # Get suggested versions
    suggested_versions = get_target_versions_for_language(primary_language)
    
    return primary_language, suggested_versions


def validate_single_file(file_path):
    """
    Validate if a single file is supported for modernization.
    
    Args:
        file_path: Path to the uploaded file
        
    Returns:
        Tuple of (is_valid, message, file_info, suggested_versions)
    """
    if not file_path:
        return False, "❌ No file uploaded", None, []
    
    try:
        file_name = Path(file_path).name
        file_ext = Path(file_path).suffix.lower()
        file_size = os.path.getsize(file_path)
        
        # Check file extension
        if file_ext not in SUPPORTED_EXTENSIONS:
            supported_list = ', '.join(sorted(SUPPORTED_EXTENSIONS))
            return False, f"❌ Unsupported file type: {file_ext}\n\n✅ Supported types:\n{supported_list}", None, []
        
        # Check file size (max 10MB for single file)
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            return False, f"❌ File too large: {file_size / 1024 / 1024:.2f} MB (max 10 MB)", None, []
        
        # Read file to check if it's valid text
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(1000)  # Read first 1000 chars
                line_count = len(content.split('\n'))
        except UnicodeDecodeError:
            return False, f"❌ File is not a valid text file (encoding error)", None, []
        
        # Detect language and get suggested versions
        language = detect_language_from_extension(file_ext)
        suggested_versions = get_target_versions_for_language(language)
        
        # Language name mapping
        language_names = {
            'python': 'Python',
            'java': 'Java',
            'javascript': 'JavaScript',
            'typescript': 'TypeScript'
        }
        
        file_info = {
            'name': file_name,
            'extension': file_ext,
            'size': file_size,
            'path': file_path,
            'language': language
        }
        
        lang_display = language_names.get(language, 'Unknown')
        
        message = f"""✅ File validated successfully!

📄 File: {file_name}
📊 Type: {file_ext} ({lang_display})
💾 Size: {file_size / 1024:.2f} KB

🎯 Suggested target versions updated in dropdown

✨ Ready to modernize! Click 'Start Modernization' button."""
        
        return True, message, file_info, suggested_versions
        
    except Exception as e:
        return False, f"❌ Error validating file: {str(e)}", None, []


def process_single_file(file_path):
    """
    Process single file upload by creating a temporary ZIP.
    
    Args:
        file_path: Path to the uploaded file
        
    Returns:
        Tuple of (status message, zip path, suggested_versions)
    """
    is_valid, message, file_info, suggested_versions = validate_single_file(file_path)
    
    if not is_valid:
        return message, None, []
    
    try:
        # Create a temporary ZIP containing the single file
        import tempfile
        import zipfile
        
        zip_path = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        with zipfile.ZipFile(zip_path.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(file_path, file_info['name'])
        
        return message, zip_path.name, suggested_versions
        
    except Exception as e:
        return f"❌ Error processing file: {str(e)}", None, []


def detect_languages_from_zip(zip_path):
    """
    Detect languages from files in a ZIP archive.
    
    Args:
        zip_path: Path to ZIP file
        
    Returns:
        Tuple of (language_summary, suggested_versions)
    """
    try:
        import zipfile
        
        file_paths = []
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            file_paths = [name for name in zipf.namelist() if not name.endswith('/')]
        
        primary_language, suggested_versions = detect_languages_from_files(file_paths)
        
        if not primary_language:
            return "Multiple file types detected", []
        
        language_names = {
            'python': 'Python',
            'java': 'Java',
            'javascript': 'JavaScript',
            'typescript': 'TypeScript'
        }
        
        return f"Primary language: {language_names.get(primary_language, 'Unknown')}", suggested_versions
        
    except Exception as e:
        logger.error(f"Error detecting languages from ZIP: {e}")
        return "Could not detect language", []


def clone_github_repo(github_url):
    """
    Clone GitHub repository and show preview.
    
    Args:
        github_url: GitHub repository URL
        
    Returns:
        Tuple of (status message, cloned repo path)
    """
    if not github_url or not github_url.strip():
        return "❌ Please enter a GitHub repository URL", None, gr.update(visible=True)
    
    try:
        import tempfile
        import subprocess
        
        # Clean URL (remove .git if present)
        github_url = github_url.strip().rstrip('/')
        if github_url.endswith('.git'):
            github_url = github_url[:-4]
        
        # Create temp directory for clone
        temp_dir = tempfile.mkdtemp(prefix="github_clone_")
        
        # Clone repository
        result = subprocess.run(
            ["git", "clone", "--depth", "1", github_url, temp_dir],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else "Unknown error"
            return f"❌ Failed to clone repository:\n{error_msg}", None, gr.update(visible=True)
        
        # Count files (only supported extensions)
        code_extensions = {'.py', '.pyw', '.pyx', '.java', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'}
        file_count = 0
        code_files = []
        
        for root, dirs, files in os.walk(temp_dir):
            # Skip .git directory
            if '.git' in root:
                continue
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, temp_dir)
                ext = os.path.splitext(file)[1].lower()
                if ext in code_extensions:
                    file_count += 1
                    code_files.append(rel_path)
        
        # Create ZIP from cloned repo
        import zipfile
        zip_path = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        with zipfile.ZipFile(zip_path.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                # Skip .git directory
                if '.git' in root:
                    continue
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        # Detect languages
        all_code_files = []
        for root, dirs, files in os.walk(temp_dir):
            if '.git' in root:
                continue
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    all_code_files.append(os.path.join(root, file))
        
        primary_language, suggested_versions = detect_languages_from_files(all_code_files)
        
        language_names = {
            'python': 'Python',
            'java': 'Java',
            'javascript': 'JavaScript',
            'typescript': 'TypeScript'
        }
        
        # Generate preview message with all files
        status = f"""✅ Repository cloned successfully!

📁 Repository: {github_url.split('/')[-1]}
📊 Code files found: {file_count}
🔤 Primary language: {language_names.get(primary_language, 'Mixed')}

📝 Loaded files ({file_count} total):
"""
        # Show all files, not just first 15
        for f in code_files:
            status += f"   • {f}\n"
        
        status += "\n🎯 Suggested target versions updated in dropdown"
        status += "\n✨ Ready to modernize! Click 'Start Modernization' button above."
        
        return status, zip_path.name, gr.update(visible=True), suggested_versions
        
    except subprocess.TimeoutExpired:
        return "❌ Clone timeout (>5 minutes). Repository might be too large.", None, gr.update(visible=True)
    except Exception as e:
        return f"❌ Error cloning from GitHub: {str(e)}", None, gr.update(visible=True)


def modernize_code(repo_file, target_version, create_pr, repo_url, github_token, cloned_repo_path, single_file_path, progress=gr.Progress()):
    """
    Main function to process uploaded repository.
    
    Args:
        repo_file: Uploaded ZIP file containing the repository
        target_version: Target language/framework version
        create_pr: Whether to create GitHub PR
        repo_url: GitHub repository URL for PR
        github_token: GitHub personal access token for PR creation
        cloned_repo_path: Path to cloned repo ZIP (if using GitHub clone)
        single_file_path: Path to single file ZIP (if using single file upload)
        progress: Gradio progress tracker
        
    Returns:
        Tuple of (status message, download files)
    """
    logger.info(f"modernize_code called with: repo_file={repo_file}, single_file_path={single_file_path}, cloned_repo_path={cloned_repo_path}")
    
    # Priority: single file > cloned repo > uploaded file
    if single_file_path:
        logger.info(f"Single file path detected: {single_file_path}")
        repo_file = type('obj', (object,), {'name': single_file_path})()
        logger.info(f"Using single file path: {single_file_path}")
    elif cloned_repo_path:
        logger.info(f"Cloned repo path detected: {cloned_repo_path}")
        repo_file = type('obj', (object,), {'name': cloned_repo_path})()
        logger.info(f"Using cloned repo path: {cloned_repo_path}")
    else:
        logger.info("Using uploaded ZIP file")
    
    # Check if any valid input source is provided
    if repo_file is None:
        logger.error("No input source provided")
        return "❌ Please upload a repository ZIP file, single file, or clone from GitHub.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
    
    logger.info(f"Processing with file: {repo_file.name}")
    
    try:
        file_path = repo_file.name
        file_size = os.path.getsize(file_path)
        
        # Initial status
        status = f"""✅ Processing started!
        
📁 File: {Path(file_path).name}
📊 Size: {file_size / 1024:.2f} KB
🎯 Target: {target_version}

"""
        progress(0.05, desc="Starting...")
        yield status, gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)  # Hide download buttons initially
        
        # Create a callback to update progress from orchestrator
        current_status = [status]  # Use list to allow modification in nested function
        
        def progress_callback(phase, message):
            """Callback to update progress from orchestrator."""
            phase_progress = {
                "Phase 1": 0.15,
                "Phase 2": 0.30,
                "Phase 3": 0.45,
                "Phase 4": 0.65,
                "Phase 5": 0.85
            }
            prog_value = phase_progress.get(phase, 0.5)
            progress(prog_value, desc=f"{phase}: {message}")
            current_status[0] += f"⏳ {phase}: {message}\n"
        
        # Run orchestrator with callback
        progress(0.1, desc="Initializing workflow...")
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        results = loop.run_until_complete(
            orchestrator.modernize_repository(
                repo_path=file_path,
                target_version=target_version,
                create_pr=create_pr,
                repo_url=repo_url if create_pr else None,
                github_token=github_token if github_token and github_token.strip() else None,
                progress_callback=progress_callback
            )
        )
        
        loop.close()
        
        progress(0.95, desc="Preparing downloads...")
        status = current_status[0]
        
        # Prepare download files
        modernized_zip = None
        tests_zip = None
        report_file = None
        
        if results.get('output'):
            import zipfile
            import tempfile
            import time
            
            # Create timestamp for file naming
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            
            output_dir = Path(results['output']['modernized_files'])
            
            # Get list of files that were actually transformed in this run
            transformed_files = []
            if results.get('phases', {}).get('transformation'):
                # Extract file paths from transformation results
                for t in results.get('transformations', []):
                    if 'file_path' in t:
                        transformed_files.append(Path(t['file_path']).name)
            
            # Create ZIP of modernized files with better naming - ONLY current run files
            if output_dir.exists() and transformed_files:
                modernized_zip = tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix='.zip',
                    prefix=f'modernized_code_{timestamp}_'
                )
                with zipfile.ZipFile(modernized_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Only include files from current transformation
                    for file in output_dir.iterdir():
                        if file.is_file() and file.name in transformed_files:
                            zipf.write(file, file.name)
                modernized_zip.close()
            else:
                modernized_zip = None
            
            # Create ZIP of test files with better naming - ONLY current run files
            tests_dir = Path(results['output']['test_files'])
            if tests_dir.exists() and transformed_files:
                tests_zip = tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix='.zip',
                    prefix=f'test_files_{timestamp}_'
                )
                with zipfile.ZipFile(tests_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Only include test files from current transformation
                    for file in tests_dir.iterdir():
                        if file.is_file():
                            # Check if this test file corresponds to a transformed file
                            test_base = file.name.replace('test_', '')
                            if test_base in transformed_files:
                                zipf.write(file, file.name)
                tests_zip.close()
            else:
                tests_zip = None
            
            # Create report file with UTF-8 encoding and better naming
            report_file = tempfile.NamedTemporaryFile(
                delete=False, 
                suffix='.txt',
                prefix=f'modernization_report_{timestamp}_',
                mode='w', 
                encoding='utf-8'
            )
            report_content = orchestrator.generate_report(results)
            report_file.write(report_content)
            report_file.close()
        
        # Generate final report
        if results['success']:
            status += "\n" + "=" * 60 + "\n"
            status += "✅ MODERNIZATION COMPLETE!\n"
            status += "=" * 60 + "\n\n"
            
            stats = results.get('statistics', {})
            status += f"📊 **Statistics:**\n"
            status += f"   • Total files: {stats.get('total_files', 0)}\n"
            status += f"   • Files modernized: {stats.get('files_modernized', 0)}\n"
            status += f"   • Tests generated: {stats.get('tests_generated', 0)}\n"
            status += f"   • Test pass rate: {stats.get('test_pass_rate', 0):.1f}%\n"
            # Only show coverage if it's greater than 0
            if stats.get('average_coverage', 0) > 0:
                status += f"   • Code coverage: {stats.get('average_coverage', 0):.1f}%\n"
            status += "\n"
            
            # Phase details
            phases = results.get('phases', {})
            
            if 'classification' in phases:
                c = phases['classification']
                status += f"📋 **Classification:**\n"
                status += f"   • High priority: {c.get('modernize_high', 0)} files\n"
                status += f"   • Low priority: {c.get('modernize_low', 0)} files\n"
                status += f"   • Skip: {c.get('skip', 0)} files\n\n"
            
            if 'search' in phases:
                s = phases['search']
                status += f"🔍 **Semantic Search:**\n"
                status += f"   • Indexed files: {s.get('indexed_files', 0)}\n"
                status += f"   • Pattern groups: {s.get('pattern_groups', 0)}\n\n"
            
            if 'validation' in phases:
                v = phases['validation']
                status += f"✅ **Validation:**\n"
                status += f"   • Tests run: {v.get('total_tests', 0)}\n"
                status += f"   • Tests passed: {v.get('tests_passed', 0)}\n"
                status += f"   • Tests failed: {v.get('tests_failed', 0)}\n"
                status += f"   • Pass rate: {v.get('pass_rate', 0):.1f}%\n"
                
                # Show execution mode
                exec_mode = v.get('execution_mode', 'unknown')
                if exec_mode == 'modal':
                    status += f"   • Execution: 🚀 Modal (cloud)\n\n"
                elif exec_mode == 'local':
                    status += f"   • Execution: 💻 Local\n\n"
                else:
                    status += f"\n"
            
            if 'github_pr' in phases:
                pr = phases['github_pr']
                if pr.get('success'):
                    status += f"🔗 **GitHub PR:**\n"
                    status += f"   • PR URL: {pr.get('pr_url', 'N/A')}\n"
                    status += f"   • PR Number: #{pr.get('pr_number', 0)}\n"
                    status += f"   • Branch: {pr.get('branch', 'N/A')}\n\n"
                else:
                    status += f"⚠️ **GitHub PR:** {pr.get('error', 'Failed')}\n\n"
            
            if results.get('errors'):
                status += f"⚠️ **Warnings:**\n"
                for error in results['errors'][:5]:
                    status += f"   • {error}\n"
            
            # Add output locations
            if results.get('output'):
                status += f"\n📁 **Output Locations:**\n"
                status += f"   • Modernized files: {results['output']['modernized_files']}\n"
                status += f"   • Test files: {results['output']['test_files']}\n"
                status += f"   • Original files: {results['output']['original_files']}\n"
            
            status += "\n" + "=" * 60 + "\n"
            status += "🎉 Ready for review and deployment!\n"
            status += "📥 Download files using the buttons below.\n"
            
        else:
            status += "\n❌ MODERNIZATION FAILED\n\n"
            status += "Errors:\n"
            for error in results.get('errors', []):
                status += f"  • {error}\n"
        
        progress(1.0, desc="Complete!")
        
        # Final yield with status and download files (make visible)
        yield (
            status, 
            gr.update(value=modernized_zip.name, visible=True) if modernized_zip else gr.update(visible=False),
            gr.update(value=tests_zip.name, visible=True) if tests_zip else gr.update(visible=False),
            gr.update(value=report_file.name, visible=True) if report_file else gr.update(visible=False)
        )
        
    except Exception as e:
        logger.error(f"Error in modernize_code: {e}", exc_info=True)
        progress(1.0, desc="Error occurred")
        yield f"❌ Error: {str(e)}\n\nPlease check logs for details.", gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)

# Custom CSS for better styling
custom_css = """
.gradio-container {
    font-family: 'Inter', sans-serif;
}
.header {
    text-align: center;
    padding: 20px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 10px;
    margin-bottom: 20px;
}
/* Style token input to match other inputs */
.token-input input {
    background-color: var(--input-background-fill) !important;
    border: 1px solid var(--input-border-color) !important;
}
"""

# Get execution mode info for display
from src.sandbox.config import EXECUTION_MODE, IS_HUGGINGFACE, MODAL_CONFIGURED

exec_mode_display = ""
if IS_HUGGINGFACE:
    if MODAL_CONFIGURED:
        exec_mode_display = "🚀 Running on Hugging Face Spaces with Modal (cloud execution)"
    else:
        exec_mode_display = "⚠️ Running on Hugging Face but Modal not configured - tests will fail!"
elif EXECUTION_MODE == "modal":
    exec_mode_display = "🚀 Modal execution enabled (cloud)"
elif EXECUTION_MODE == "local":
    exec_mode_display = "💻 Local execution mode"
else:
    exec_mode_display = ""  # Don't show anything for auto mode

# Build Gradio interface
with gr.Blocks(title="Legacy Code Modernizer") as app:
    # Add custom CSS via HTML
    gr.HTML(f"""
        <style>
        {custom_css}
        </style>
        <div class="header">
            <h1>🤖 Legacy Code Modernizer</h1>
            <p>AI-powered code modernization for Python, Java, and JavaScript/TypeScript</p>
            <p style="font-size: 12px; opacity: 0.8; margin-top: 8px;">{exec_mode_display}</p>
        </div>
    """)
    
    gr.Markdown("""
    ### Modernization Workflow:
    1. **Discovery & Classification**: Analyze codebase structure and prioritize files
    2. **Semantic Search**: Group similar patterns using vector-based search
    3. **Code Transformation**: Apply AI-powered modernization patterns
    4. **Testing & Validation**: Generate tests and validate in secure sandbox
    5. **GitHub Integration**: Create pull requests with comprehensive documentation
    
    **Powered by**: Google Gemini, Nebius AI, LlamaIndex, Chroma, Modal, MCP Protocol
    """)
    
    with gr.Row():
        with gr.Column(scale=2):
            # Input method selection
            with gr.Tabs() as input_tabs:
                with gr.Tab("📄 Single File"):
                    single_file_input = gr.File(
                        label="Upload Single Code File",
                        file_types=[
                            ".py", ".pyw", ".pyx",
                            ".java",
                            ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"
                        ],
                        type="filepath"
                    )
                    
                    file_status = gr.Textbox(
                        label="File Status",
                        lines=8,
                        interactive=False,
                        visible=True
                    )
                    
                    single_file_path = gr.State(value=None)
                    
                    gr.Markdown("""
                    **Supported Languages**:
                    - Python (.py, .pyw, .pyx) - pytest with coverage
                    - Java (.java) - Maven + JUnit 5 + JaCoCo
                    - JavaScript (.js, .jsx, .mjs, .cjs) - Jest with coverage
                    - TypeScript (.ts, .tsx) - Jest with coverage
                    
                    **Max file size**: 10 MB per file
                    
                    **Note**: All supported languages include code transformation, test generation, and secure Modal sandbox execution with automatic dependency management.
                    """)
                
                with gr.Tab("📁 Upload ZIP"):
                    file_input = gr.File(
                        label="Upload Repository (.zip)",
                        file_types=[".zip"],
                        type="filepath"
                    )
                
                with gr.Tab("🔗 Clone from GitHub"):
                    github_repo_url = gr.Textbox(
                        label="GitHub Repository URL",
                        placeholder="https://github.com/owner/repo",
                        info="Enter full GitHub URL to clone (without .git extension)"
                    )
                    
                    clone_btn = gr.Button(
                        "📥 Load Repository",
                        variant="secondary",
                        size="sm"
                    )
                    
                    clone_status = gr.Textbox(
                        label="Repository Files",
                        lines=15,
                        interactive=False,
                        visible=False
                    )
                    
                    cloned_repo_path = gr.State(value=None)
                    
                    gr.Markdown("**Note**: Requires git to be installed on your system")
            
            # Build comprehensive target version list
            all_target_versions = []
            for versions in TARGET_VERSIONS.values():
                all_target_versions.extend(versions)
            all_target_versions.extend(FRAMEWORK_VERSIONS)
            all_target_versions = sorted(set(all_target_versions))
            
            target_version = gr.Dropdown(
                choices=all_target_versions,
                label="🎯 Target Version (auto-detected from files)",
                value="Python 3.14",
                info="Automatically updated based on uploaded files",
                allow_custom_value=False
            )
            
            # Add option to select from full list
            with gr.Accordion("📋 Browse All Versions", open=False):
                gr.Markdown("""
                **Auto-detection incorrect?** Select from the full list below:
                
                **Python**: 3.14, 3.13, 3.12, 3.11, 3.10
                **Java**: 25 LTS, 23, 21 LTS, 17 LTS
                **JavaScript**: ES2025, ES2024, Node.js 25, 24 LTS, 22 LTS
                **TypeScript**: 5.9, 5.8, 5.7, 5.6
                
                **Frameworks**: React 19, Angular 21, Vue 3.5, Django 5.2 LTS, Spring Boot 4.0, Laravel 12, Rails 8.1, Next.js 16, FastAPI 0.122, and more
                
                Simply select your desired version from the dropdown above.
                """)
            
            with gr.Accordion("⚙️ Advanced Options", open=False):
                create_pr = gr.Checkbox(
                    label="Create GitHub PR",
                    value=False,
                    info="Automatically create pull request with modernized code"
                )
                
                repo_url = gr.Textbox(
                    label="GitHub Repository URL for PR",
                    placeholder="owner/repo (e.g., myorg/myproject)",
                    info="Required if creating PR"
                )
                
                github_token_input = gr.Textbox(
                    label="GitHub Personal Access Token",
                    placeholder="ghp_xxxxxxxxxxxxxxxxxxxx",
                    type="password",
                    info="Required for PR creation. Leave empty to use token from .env file",
                    container=True,
                    elem_classes=["token-input"]
                )
            
            process_btn = gr.Button(
                "🚀 Start Modernization",
                variant="primary",
                size="lg"
            )
        
        with gr.Column(scale=3):
            output = gr.Textbox(
                label="📊 Status & Progress",
                lines=25,
                max_lines=35
            )
    
    # Download section (separate row, below main interface)
    with gr.Row():
        download_modernized = gr.File(
            label="📦 Download Modernized Code",
            visible=False
        )
        download_tests = gr.File(
            label="🧪 Download Test Files",
            visible=False
        )
        download_report = gr.File(
            label="📄 Download Report",
            visible=False
        )
    
    with gr.Accordion("📖 Features & Capabilities", open=False):
        gr.Markdown("""
        ### Core Features:
        
        **🔍 Semantic Code Search**
        - Vector-based similarity search using LlamaIndex and Chroma
        - Automatic pattern grouping for efficient refactoring
        - Bulk code transformation capabilities
        
        **🤖 AI-Powered Analysis**
        - Powered by Google Gemini and Nebius AI models
        - Large context window for comprehensive code understanding
        - Multi-language support (Python, Java, JavaScript, TypeScript)
        
        **🧪 Automated Testing**
        - Isolated test execution in Modal sandbox
        - Secure environment with no network access
        - Performance benchmarking and coverage reporting
        
        **🔗 GitHub Integration**
        - Automated pull request creation via MCP Protocol
        - Comprehensive documentation generation
        - Deployment checklists and rollback plans
        
        **📊 Quality Assurance**
        - High test pass rates with comprehensive coverage
        - Behavioral equivalence testing
        - Automated validation before deployment
        """)
    
    with gr.Accordion("🎯 Supported Languages & Versions", open=False):
        gr.Markdown("""
        ### Supported Languages (Updated November 2025):
        
        **Python**
        - Versions: 3.9, 3.10, 3.11, 3.12, 3.13
        - Frameworks: Django 5.1, Flask 3.1, FastAPI 0.115
        - Testing: pytest with coverage
        
        **Java**
        - Versions: Java 11 LTS, 17 LTS, 21 LTS, 23
        - Frameworks: Spring Boot 3.4
        - Testing: Maven + JUnit 5 + JaCoCo
        
        **JavaScript**
        - Standards: ES2023, ES2024, ES2025
        - Runtimes: Node.js 20 LTS, 22 LTS, 23
        - Frameworks: React 19, Angular 19, Vue 3.5, Express 5.0, Next.js 15
        - Testing: Jest with coverage
        
        **TypeScript**
        - Versions: 5.4, 5.5, 5.6, 5.7
        - Frameworks: React 19, Angular 19, Vue 3.5, Next.js 15
        - Testing: Jest with ts-jest
        """)
    
    # State for suggested versions
    suggested_versions_state = gr.State(value=[])
    
    # Event handlers
    # Handle single file validation (automatic on upload)
    def validate_and_show(file_path):
        """Wrapper to validate file and show status."""
        logger.info(f"validate_and_show called with file_path: {file_path}")
        if not file_path:
            logger.warning("No file path provided to validate_and_show")
            return "📄 Upload a code file to get started", None, gr.update(), []
        
        try:
            message, zip_path, suggested_versions = process_single_file(file_path)
            logger.info(f"Validation result: message='{message}', zip_path='{zip_path}', versions={len(suggested_versions)}")
            
            # Update dropdown with suggested versions
            if suggested_versions:
                return message, zip_path, gr.update(choices=suggested_versions, value=suggested_versions[0]), suggested_versions
            else:
                return message, zip_path, gr.update(), []
        except Exception as e:
            logger.error(f"Error in validate_and_show: {e}", exc_info=True)
            return f"❌ Error: {str(e)}", None, gr.update(), []
    
    # Handle ZIP file upload
    def handle_zip_upload(file_path):
        """Handle ZIP file upload and detect languages."""
        if not file_path:
            return gr.update(), []
        
        try:
            lang_summary, suggested_versions = detect_languages_from_zip(file_path)
            logger.info(f"ZIP upload: {lang_summary}, {len(suggested_versions)} versions")
            
            if suggested_versions:
                return gr.update(choices=suggested_versions, value=suggested_versions[0]), suggested_versions
            else:
                return gr.update(), []
        except Exception as e:
            logger.error(f"Error handling ZIP upload: {e}")
            return gr.update(), []
    
    # Auto-validate on file upload
    single_file_input.change(
        fn=validate_and_show,
        inputs=[single_file_input],
        outputs=[file_status, single_file_path, target_version, suggested_versions_state],
        show_progress=True
    )
    
    # Auto-detect on ZIP upload
    file_input.change(
        fn=handle_zip_upload,
        inputs=[file_input],
        outputs=[target_version, suggested_versions_state],
        show_progress=False
    )
    
    # Handle GitHub clone button
    def handle_github_clone(github_url):
        """Wrapper for GitHub clone with version detection."""
        status, zip_path, visibility, suggested_versions = clone_github_repo(github_url)
        
        if suggested_versions:
            return status, zip_path, visibility, gr.update(choices=suggested_versions, value=suggested_versions[0]), suggested_versions
        else:
            return status, zip_path, visibility, gr.update(), []
    
    clone_btn.click(
        fn=handle_github_clone,
        inputs=[github_repo_url],
        outputs=[clone_status, cloned_repo_path, clone_status, target_version, suggested_versions_state],
        show_progress=True
    )
    
    # Handle modernization
    process_btn.click(
        fn=modernize_code,
        inputs=[file_input, target_version, create_pr, repo_url, github_token_input, cloned_repo_path, single_file_path],
        outputs=[output, download_modernized, download_tests, download_report],
        show_progress="full"
    )
    
    # Examples
    gr.Examples(
        examples=[
            [None, "Python 3.12", False, "", "", None, None],
            [None, "Java 21 LTS", False, "", "", None, None],
            [None, "React 18 (Hooks)", True, "myorg/myproject", "", None, None]
        ],
        inputs=[file_input, target_version, create_pr, repo_url, github_token_input, cloned_repo_path, single_file_path],
        label="📝 Example Configurations"
    )
    


if __name__ == "__main__":
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        css=custom_css
    )
