# Kilo Code Usage Rules

## Development Environment Rules

### 1. Package Installation
**Rule**: Do not use `--break-system-packages` to install packages in system environment.

**Rationale**: Using `--break-system-packages` can break system Python installations and cause conflicts with system packages. This ensures we maintain a clean development environment.

**Implementation**:
- Always use virtual environments for Python development
- Use `python -m venv venv` to create virtual environments
- Use `pip install` within activated virtual environments
- For Docker environments, ensure proper isolation

### 2. Virtual Environment
**Rule**: Never try to create virtual environment, if you detect you cannot perform action due to not being in Virtual environment, stop action and ask.

### 3. Code Modification Philosophy
**Rule**: When adding new functionality to existing project, try to use existing codebase and make as little change as possible and make as least new function as possible. When introducing changes, make sure to include default setting the mimic the action before change to prevent breaking code and preserve compatibility.

**Guidelines**:
- **Backward Compatibility**: Always maintain backward compatibility
- **Minimal Changes**: Modify existing functions rather than creating new ones when possible
- **Default Parameters**: Use default parameter values to preserve existing behavior
- **Feature Flags**: Implement feature toggles for new functionality
- **Deprecation**: Mark deprecated features clearly with migration paths

## Enforcement

These rules are automatically enforced by:
1. Development environment checks in setup scripts
2. Code review guidelines
3. Pre-commit hooks (when applicable)
4. Continuous integration pipeline

## Updates

This file should be updated when:
- New development patterns are established
- Tool requirements change
- Team conventions evolve
- New compatibility issues are discovered

**Last updated**: 2025-07-28