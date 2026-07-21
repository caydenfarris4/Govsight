# GovSight Requirements Management

This directory contains organized requirement files for different deployment scenarios of the GovSight Financial Analyzer.

## Requirements Files

### `base.txt`
Core dependencies required for basic application functionality:
- Streamlit web framework
- Data processing libraries (pandas, numpy)
- Database connectivity
- Visualization tools (plotly, matplotlib)
- AI integration (OpenAI, Anthropic)
- Document processing

### `development.txt`
Additional tools for development and testing:
- Testing frameworks (pytest, coverage)
- Code quality tools (black, flake8, mypy)
- Documentation tools (sphinx)
- Security testing (bandit, safety)
- Performance profiling tools

### `production.txt`
Production deployment optimizations:
- Web servers (gunicorn, uvicorn)
- Monitoring and logging
- Performance optimization tools
- Security hardening
- Health monitoring

### `security.txt`
Enhanced security dependencies:
- Advanced cryptography libraries
- Input validation and sanitization
- Session management tools
- Security headers
- Threat detection tools

## Installation

### For Development
```bash
pip install -r modules/requirements/development.txt
```

### For Production Deployment
```bash
pip install -r modules/requirements/production.txt
```

### For Maximum Security
```bash
pip install -r modules/requirements/base.txt
pip install -r modules/requirements/security.txt
```

### Individual Environment
```bash
# Base installation only
pip install -r modules/requirements/base.txt

# Security enhancements only
pip install -r modules/requirements/security.txt
```

## Validation

Run the requirements validation:
```bash
python modules/requirements/__init__.py
```

This will check that all requirements files exist and provide dependency counts.

## Maintenance

### Adding New Dependencies
1. Identify the appropriate requirements file based on the dependency's purpose
2. Add the dependency with version specification
3. Test the installation in a clean environment
4. Update this README if adding new categories

### Version Updates
- Use semantic versioning (>=, ~=, ==) appropriately
- Test compatibility before updating major versions
- Pin critical dependencies for production stability

### Environment-Specific Notes

#### Development
- Includes all tools needed for local development
- May include packages not needed in production
- Version constraints can be more flexible

#### Production
- Focuses on runtime performance and monitoring
- More strict version pinning for stability
- Includes deployment-specific tools

#### Security
- Enhanced cryptography and validation libraries
- Threat detection and monitoring tools
- Can be combined with other requirement files

## Integration with Replit

The requirements files are designed to work with Replit's package management system. The main dependencies are also specified in `replit.nix` for the Nix environment.

## Dependency Management Best Practices

1. **Version Pinning**: Use `>=` for flexibility, `==` for strict requirements
2. **Security**: Regularly update dependencies for security patches
3. **Testing**: Test all requirement combinations before deployment
4. **Documentation**: Keep this README updated with any changes
5. **Separation**: Keep environment-specific dependencies in appropriate files