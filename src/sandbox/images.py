"""
Modal Container Images for Multi-Language Test Execution.
Defines secure, isolated container images for each supported language.
"""

import logging

logger = logging.getLogger(__name__)

# Try to import Modal
try:
    import modal
    MODAL_AVAILABLE = True
except ImportError:
    MODAL_AVAILABLE = False
    modal = None
    logger.warning("Modal not available - will use local execution only")

# Create Modal app only if available
if MODAL_AVAILABLE:
    app = modal.App("legacy-code-validator")
    
    # ============================================================================
    # SUPPORTED LANGUAGES (Production Ready)
    # ============================================================================
    
    python_image = (
        modal.Image.debian_slim()
        .pip_install(
            "pytest>=9.0.0",
            "pytest-cov>=6.0.0",
            "pytest-timeout>=2.3.0",
            "pytest-benchmark>=4.0.0",
            "pytest-mock>=3.12.0"
        )
    )
    
    java_image = (
        modal.Image.debian_slim()
        .apt_install("openjdk-17-jdk", "maven", "wget")
        .run_commands(
            "mvn --version"
        )
    )
    
    javascript_image = (
        modal.Image.debian_slim()
        .apt_install(
            "curl", "ca-certificates", "gnupg", "libxt6", "libxmu6", "libxaw7",
            "build-essential", "python3", "git"
        )
        .run_commands(
            # Install Node.js 20.x
            "mkdir -p /etc/apt/keyrings",
            "curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg",
            "echo 'deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main' | tee /etc/apt/sources.list.d/nodesource.list",
            "apt-get update",
            "apt-get install -y nodejs",
            # Pre-install Jest globally for faster test execution
            "npm install -g jest@latest ts-jest@latest typescript@latest @types/jest@latest",
            # Create a working directory and set permissions
            "mkdir -p /workspace",
            "chmod 777 /workspace",
            "node --version",
            "npm --version",
            "jest --version"
        )
    )
    
    # TypeScript uses same image as JavaScript
    typescript_image = javascript_image
    
    # ============================================================================
    # IMAGE REGISTRY
    # ============================================================================
    
    LANGUAGE_IMAGES = {
        # Supported Languages
        'python': python_image,
        'java': java_image,
        'javascript': javascript_image,
        'typescript': typescript_image
    }
    
    # Support status for UI display
    LANGUAGE_SUPPORT_STATUS = {
        'python': 'production',
        'java': 'production',
        'javascript': 'production',
        'typescript': 'production'
    }
    
else:
    # Fallback when Modal not available
    app = None
    LANGUAGE_IMAGES = {}
    LANGUAGE_SUPPORT_STATUS = {}
    python_image = None
    java_image = None
    javascript_image = None
    typescript_image = None


def get_image_for_language(language: str):
    """Get the appropriate Modal image for a language."""
    if not MODAL_AVAILABLE:
        return None
    
    return LANGUAGE_IMAGES.get(language.lower())


def get_support_status(language: str) -> str:
    """Get support status for a language: production, experimental, planned, or unsupported."""
    if not MODAL_AVAILABLE:
        return 'local_only'
    
    return LANGUAGE_SUPPORT_STATUS.get(language.lower(), 'unsupported')


def is_language_supported(language: str) -> bool:
    """Check if a language is supported in Modal."""
    return language.lower() in LANGUAGE_IMAGES
