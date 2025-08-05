# Kilo Code Usage Rules

### 2. File Removal
**Rule**: Do Not Delete any file. If some file is supposed to be removed, add a "REMOVE_<UUID>_" tag to the front and leave it as is. I will determine if it needed to be removed.

## Development Environment Rules
### 2. Virtual Environment Management
**Rule**: Don't use virtual environment

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