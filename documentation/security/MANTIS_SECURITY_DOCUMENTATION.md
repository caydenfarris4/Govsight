# Mantis Security Documentation
## Enterprise-Grade Data Protection for Municipal Financial Documents

### Overview
Mantis implements comprehensive security measures to protect sensitive municipal financial data during document upload and analysis. All security features are designed to ensure data never leaves the secure processing environment.

### Security Features

#### 🔒 **Memory-Only Processing**
- Files are processed entirely in memory
- No permanent disk storage or temporary file creation
- Data exists only during active session
- Automatic memory cleanup on session end

#### 🛡️ **File Validation & Sanitization**
- Comprehensive file type validation (PDF, CSV only)
- File size limits (50MB maximum)
- Content sanitization to remove malicious patterns
- SQL injection protection
- HTML/XML tag removal
- Dangerous script pattern filtering

#### 🕒 **Session Security**
- 1-hour automatic session timeout
- Forced data cleanup on timeout
- Session isolation between users
- User-controlled manual data clearing

#### 📊 **Access Logging & Audit Trail**
- Complete file access event logging
- Security validation tracking
- Error event documentation
- File integrity hash verification
- Timestamp tracking for all operations

#### 🔍 **Data Processing Security**
- Text content length limits (1MB maximum)
- DataFrame size restrictions (100,000 rows maximum)
- Column name sanitization
- Statistical summary generation without exposing sensitive patterns
- Security hash generation for file integrity

### Security Architecture

#### File Upload Flow
1. **File Reception** → Security validation
2. **Type & Size Check** → Content sanitization
3. **Memory Processing** → Data extraction
4. **Secure Storage** → Session state only
5. **Analysis** → AI processing with context
6. **Cleanup** → Automatic or manual clearing

#### Data Protection Layers
- **Layer 1**: File type and size validation
- **Layer 2**: Content sanitization and filtering
- **Layer 3**: Memory-only processing
- **Layer 4**: Session timeout enforcement
- **Layer 5**: Audit logging and monitoring

### User Security Controls

#### Security Information Panel
Users can view current security status including:
- Session timeout settings
- File size limits
- Allowed file types
- Active security features

#### Manual Security Controls
- **Clear All Files**: Immediate secure data removal
- **Security Status**: Real-time security monitoring
- **File Count Tracking**: Visibility of files in memory

### Security Logging

All file operations are logged with:
- Session ID
- File name and hash
- File size
- Action performed
- Timestamp
- User agent information

#### Logged Events
- `VALIDATED` - File passed security checks
- `PROCESSING_PDF` - PDF processing started
- `PROCESSING_CSV` - CSV processing started
- `PROCESSED_PDF` - PDF successfully processed
- `PROCESSED_CSV` - CSV successfully processed
- `REJECTED_SIZE` - File rejected for size
- `REJECTED_TYPE` - File rejected for type
- `ERROR_PDF` - PDF processing error
- `ERROR_CSV` - CSV processing error
- `CRITICAL_ERROR` - System error during processing
- `CLEARED` - File data cleared from memory

### Technical Implementation

#### SecureFileHandler Class
- **validate_file_security()**: Comprehensive file validation
- **process_pdf_securely()**: Memory-only PDF processing
- **process_csv_securely()**: Secure DataFrame creation
- **sanitize_text_content()**: Content filtering
- **sanitize_dataframe()**: Data structure security
- **enforce_session_timeout()**: Automatic cleanup
- **clear_file_data()**: Manual security clearing

### Compliance & Best Practices

#### Municipal Data Protection
- Meets government data handling requirements
- Ensures sensitive financial information protection
- Provides audit trail for compliance
- Implements data retention controls

#### Security Best Practices
- Zero-persistence file handling
- Comprehensive input validation
- Session-based security isolation
- Complete audit logging
- User-controlled data lifecycle

### Security Verification

Users can verify security through:
- Real-time security status display
- File processing confirmations
- Security hash verification
- Audit log accessibility
- Clear data lifecycle indicators

---

**Note**: This security system is specifically designed for sensitive municipal financial documents and implements enterprise-grade protection measures to ensure data confidentiality and integrity throughout the analysis process.