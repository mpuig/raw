"""RAW Platform code generation package.

Provides code generation, validation, and sandboxing for the creator functionality.
"""

from raw_codegen.generator import (
    CodeGenContext,
    CodeGenerator,
    InputSpec,
    OutputSpec,
    create_generator,
)
from raw_codegen.sandbox import (
    CodeSandbox,
    ExecutionResult,
    MockEnvironment,
    SandboxError,
    execute_script,
    execute_source,
)
from raw_codegen.validator import (
    CodeValidator,
    DangerousOperationDetector,
    FunctionAnalyzer,
    ImportAnalyzer,
    ValidationIssue,
    ValidationResult,
    validate_code,
    validate_file,
)

__all__ = [
    # Generator
    "CodeGenerator",
    "CodeGenContext",
    "InputSpec",
    "OutputSpec",
    "create_generator",
    # Validator
    "CodeValidator",
    "ValidationResult",
    "ValidationIssue",
    "validate_code",
    "validate_file",
    "DangerousOperationDetector",
    "ImportAnalyzer",
    "FunctionAnalyzer",
    # Sandbox
    "CodeSandbox",
    "ExecutionResult",
    "SandboxError",
    "execute_script",
    "execute_source",
    "MockEnvironment",
]

__version__ = "0.1.0"
