"""
Sandbox execution configuration.
Handles environment-specific settings for local vs Hugging Face deployment.
"""

import os
import logging

logger = logging.getLogger(__name__)


def is_huggingface_space() -> bool:
    """Detect if running in Hugging Face Spaces environment."""
    return os.getenv("SPACE_ID") is not None or os.getenv("SYSTEM") == "spaces"


def is_modal_configured() -> bool:
    """Check if Modal is properly configured with credentials."""
    # Check for Modal token in environment
    token_id = os.getenv("MODAL_TOKEN_ID")
    token_secret = os.getenv("MODAL_TOKEN_SECRET")
    
    # Check if modal config exists
    modal_config_exists = os.path.exists(os.path.expanduser("~/.modal.toml"))
    
    return bool((token_id and token_secret) or modal_config_exists)


def get_execution_mode() -> str:
    """
    Determine the execution mode based on environment.
    
    Returns:
        "modal" - Use Modal for execution (required for Hugging Face)
        "local" - Use local subprocess execution
        "auto" - Try Modal first, fallback to local
    """
    # Explicit mode from environment
    mode = os.getenv("EXECUTION_MODE", "").lower()
    if mode in ("modal", "local", "auto"):
        return mode
    
    # Auto-detect based on environment
    if is_huggingface_space():
        # Hugging Face Spaces MUST use Modal
        if is_modal_configured():
            logger.info("Hugging Face Spaces detected - using Modal execution")
            return "modal"
        else:
            logger.error("Hugging Face Spaces detected but Modal not configured!")
            logger.error("Set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET environment variables")
            return "modal"  # Still return modal, will fail with clear error
    
    # Local development - try Modal first, fallback to local
    if is_modal_configured():
        return "auto"
    else:
        logger.info("Modal not configured - using local execution")
        return "local"


def should_prefer_modal() -> bool:
    """Determine if Modal should be preferred over local execution."""
    mode = get_execution_mode()
    
    if mode == "modal":
        return True
    elif mode == "local":
        return False
    else:  # auto
        return is_modal_configured()


def validate_environment():
    """
    Validate that the environment is properly configured.
    Raises warnings or errors for configuration issues.
    """
    mode = get_execution_mode()
    is_hf = is_huggingface_space()
    modal_ok = is_modal_configured()
    
    if is_hf and not modal_ok:
        logger.error("=" * 60)
        logger.error("CONFIGURATION ERROR: Hugging Face Spaces Deployment")
        logger.error("=" * 60)
        logger.error("Modal is REQUIRED for Hugging Face Spaces but not configured.")
        logger.error("")
        logger.error("To fix this:")
        logger.error("1. Get Modal token from: https://modal.com/settings")
        logger.error("2. Set Hugging Face Secrets:")
        logger.error("   - MODAL_TOKEN_ID")
        logger.error("   - MODAL_TOKEN_SECRET")
        logger.error("3. Restart the Space")
        logger.error("=" * 60)
        return False
    
    if mode == "modal" and not modal_ok:
        logger.warning("Execution mode set to 'modal' but Modal not configured")
        logger.warning("Tests will fail until Modal is configured")
        return False
    
    if mode == "local" and is_hf:
        logger.warning("Local execution mode on Hugging Face Spaces will not work")
        logger.warning("Change EXECUTION_MODE to 'modal'")
        return False
    
    # All good
    logger.info(f"Environment validated: mode={mode}, huggingface={is_hf}, modal_configured={modal_ok}")
    return True


# Configuration values
EXECUTION_MODE = get_execution_mode()
PREFER_MODAL = should_prefer_modal()
IS_HUGGINGFACE = is_huggingface_space()
MODAL_CONFIGURED = is_modal_configured()

# Log configuration on import
logger.info(f"Sandbox Configuration:")
logger.info(f"  Execution Mode: {EXECUTION_MODE}")
logger.info(f"  Prefer Modal: {PREFER_MODAL}")
logger.info(f"  Hugging Face: {IS_HUGGINGFACE}")
logger.info(f"  Modal Configured: {MODAL_CONFIGURED}")
