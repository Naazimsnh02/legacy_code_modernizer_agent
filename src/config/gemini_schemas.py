"""
JSON schemas for Gemini API responses.
Ensures structured, predictable outputs from the AI model.

Note: Uses Google GenAI SDK schema format (uppercase types: STRING, NUMBER, etc.)
"""

from typing import Dict, Any


class GeminiSchemas:
    """Collection of JSON schemas for different response types."""
    
    @staticmethod
    def language_detection() -> Dict[str, Any]:
        """Schema for language and framework detection."""
        return {
            "type": "OBJECT",
            "properties": {
                "language": {
                    "type": "STRING",
                    "description": "Detected programming language"
                },
                "framework": {
                    "type": "STRING",
                    "description": "Detected framework or empty string if none",
                    "nullable": True
                },
                "confidence": {
                    "type": "NUMBER",
                    "description": "Confidence score between 0.0 and 1.0"
                }
            },
            "required": ["language", "framework", "confidence"]
        }
    
    @staticmethod
    def pattern_analysis() -> Dict[str, Any]:
        """Schema for pattern analysis results."""
        return {
            "type": "OBJECT",
            "properties": {
                "patterns": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "pattern_type": {"type": "STRING"},
                            "severity": {
                                "type": "STRING",
                                "enum": ["critical", "high", "medium", "low", "info"]
                            },
                            "line_numbers": {
                                "type": "ARRAY",
                                "items": {"type": "INTEGER"}
                            },
                            "confidence": {
                                "type": "NUMBER"
                            },
                            "description": {"type": "STRING"},
                            "recommendation": {"type": "STRING"},
                            "estimated_effort_hours": {
                                "type": "NUMBER"
                            }
                        },
                        "required": [
                            "pattern_type", "severity", "line_numbers",
                            "confidence", "description", "recommendation",
                            "estimated_effort_hours"
                        ]
                    }
                },
                "modernization_score": {
                    "type": "INTEGER"
                },
                "requires_modernization": {"type": "BOOLEAN"},
                "overall_priority": {
                    "type": "STRING",
                    "enum": ["critical", "high", "medium", "low", "info"]
                }
            },
            "required": [
                "patterns", "modernization_score",
                "requires_modernization", "overall_priority"
            ]
        }
    
    @staticmethod
    def batch_pattern_analysis() -> Dict[str, Any]:
        """Schema for batch pattern analysis results."""
        return {
            "type": "OBJECT",
            "properties": {
                "files": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "file_path": {"type": "STRING"},
                            "language": {"type": "STRING"},
                            "framework": {
                                "type": "STRING",
                                "nullable": True
                            },
                            "patterns": {
                                "type": "ARRAY",
                                "items": {
                                    "type": "OBJECT",
                                    "properties": {
                                        "pattern_type": {"type": "STRING"},
                                        "severity": {
                                            "type": "STRING",
                                            "enum": ["critical", "high", "medium", "low", "info"]
                                        },
                                        "line_numbers": {
                                            "type": "ARRAY",
                                            "items": {"type": "INTEGER"}
                                        },
                                        "confidence": {
                                            "type": "NUMBER"
                                        },
                                        "description": {"type": "STRING"},
                                        "recommendation": {"type": "STRING"},
                                        "estimated_effort_hours": {
                                            "type": "NUMBER"
                                        }
                                    },
                                    "required": [
                                        "pattern_type", "severity", "line_numbers",
                                        "confidence", "description", "recommendation",
                                        "estimated_effort_hours"
                                    ]
                                }
                            },
                            "modernization_score": {
                                "type": "INTEGER"
                            },
                            "requires_modernization": {"type": "BOOLEAN"},
                            "overall_priority": {
                                "type": "STRING",
                                "enum": ["critical", "high", "medium", "low", "info"]
                            }
                        },
                        "required": [
                            "file_path", "language", "framework", "patterns",
                            "modernization_score", "requires_modernization",
                            "overall_priority"
                        ]
                    }
                }
            },
            "required": ["files"]
        }
    
    @staticmethod
    def file_classification() -> Dict[str, Any]:
        """Schema for file classification results."""
        return {
            "type": "OBJECT",
            "properties": {
                "classification": {
                    "type": "STRING",
                    "enum": ["primary", "secondary", "test", "config", "documentation"]
                },
                "confidence": {
                    "type": "NUMBER"
                },
                "reasoning": {"type": "STRING"},
                "language": {"type": "STRING"},
                "framework": {
                    "type": "STRING",
                    "nullable": True
                }
            },
            "required": ["classification", "confidence", "reasoning", "language", "framework"]
        }
    
    @staticmethod
    def code_analysis() -> Dict[str, Any]:
        """Schema for detailed code analysis."""
        return {
            "type": "OBJECT",
            "properties": {
                "summary": {"type": "STRING"},
                "issues": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "type": {"type": "STRING"},
                            "severity": {
                                "type": "STRING",
                                "enum": ["critical", "high", "medium", "low", "info"]
                            },
                            "description": {"type": "STRING"},
                            "line_numbers": {
                                "type": "ARRAY",
                                "items": {"type": "INTEGER"}
                            },
                            "recommendation": {"type": "STRING"}
                        },
                        "required": ["type", "severity", "description", "line_numbers", "recommendation"]
                    }
                },
                "transformation_steps": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "step": {"type": "STRING"},
                            "description": {"type": "STRING"},
                            "priority": {
                                "type": "STRING",
                                "enum": ["critical", "high", "medium", "low"]
                            },
                            "estimated_hours": {
                                "type": "NUMBER"
                            }
                        },
                        "required": ["step", "description", "priority", "estimated_hours"]
                    }
                },
                "dependencies": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                },
                "estimated_total_hours": {
                    "type": "NUMBER"
                }
            },
            "required": [
                "summary", "issues", "transformation_steps",
                "dependencies", "estimated_total_hours"
            ]
        }
    
    @staticmethod
    def test_generation() -> Dict[str, Any]:
        """Schema for test generation metadata."""
        return {
            "type": "OBJECT",
            "properties": {
                "test_framework": {"type": "STRING"},
                "test_count": {
                    "type": "INTEGER"
                },
                "coverage_areas": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                },
                "test_types": {
                    "type": "ARRAY",
                    "items": {
                        "type": "STRING",
                        "enum": ["unit", "integration", "edge_case", "error_handling"]
                    }
                },
                "notes": {"type": "STRING"}
            },
            "required": ["test_framework", "test_count", "coverage_areas", "test_types", "notes"]
        }
