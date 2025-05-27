# EML Editor Web Application

A user-friendly web interface for modifying EML files with all the features of the command-line tools.

## Features

- 📧 **Upload EML files** through a web browser
- 📅 **Change email date** with date/time picker
- ✏️ **Edit email body** in a text editor
- 📎 **Manage attachments** - add, remove files
- 🔧 **Modify headers** - From, To, Subject
- 🔐 **Cryptographic signing** (optional)
- 💾 **Download modified EML** file

## Installation

### Basic Setup (No Crypto)

```bash
# Install Flask
pip install Flask Werkzeug

# Run the application
python web_app.py
```

### Full Setup (With Crypto)

```bash
# Install all dependencies
pip install -r requirements_web.txt

# Run the application
python web_app.py
```

## Usage

1. **Start the server:**
   ```bash
   python web_app.py
   ```

2. **Open your browser:**
   Navigate to `http://localhost:5000`

3. **Upload and modify:**
   - Click "Upload" to select your EML file
   - Modify the date, body, and attachments as needed
   - Click "Process Email" to apply changes
   - Download the modified file

## Web Interface Screenshots

### 1. Upload Page
- Simple drag-and-drop or click to upload
- Shows available features
- File size limit: 16MB

### 2. Modification Page
Shows current email information and provides forms to:
- **Headers Section**: Modify From, To, Subject, Date
- **Body Section**: Edit email content
- **Attachments Section**: Remove existing or add new files
- **Security Options**: Enable real DKIM/ARC signatures (if available)

### 3. Download Page
- Success confirmation
- Download button for modified email
- Option to process another file

## API Endpoints

- `GET /` - Main upload page
- `POST /upload` - Handle file upload
- `POST /process` - Process modifications
- `GET /download/<filename>` - Download modified file

## File Structure

```
.
├── web_app.py              # Flask application
├── templates/              # HTML templates
│   ├── index.html         # Upload page
│   └── modify.html        # Modification form
├── static/                # Static assets
│   ├── css/
│   │   └── style.css     # Custom styles
│   └── js/
│       └── modify.js     # Form handling
├── uploads/               # Temporary upload storage
└── outputs/               # Modified files
```

## Security Features

- File type validation (only .eml files)
- Secure filename handling
- Automatic cleanup of old files (1 hour)
- CSRF protection with Flask sessions
- Maximum file size limit (16MB)

## Configuration

Edit these variables in `web_app.py`:

```python
app.secret_key = 'your-secret-key-here'  # Change in production!
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
```

## Deployment

### Development Server

```bash
python web_app.py
```

### Production Deployment

For production, use a proper WSGI server:

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 web_app:app
```

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements_web.txt .
RUN pip install -r requirements_web.txt

COPY . .

RUN mkdir -p uploads outputs

EXPOSE 5000

CMD ["python", "web_app.py"]
```

Build and run:

```bash
docker build -t eml-editor-web .
docker run -p 5000:5000 eml-editor-web
```

## Troubleshooting

**"Upload failed"**
- Check file is .eml format
- Ensure file is under 16MB
- Check uploads/ directory exists and is writable

**"Crypto features not available"**
- Install crypto dependencies: `pip install -r requirements.txt`

**"Internal server error"**
- Check console for detailed error messages
- Ensure all Python modules are installed
- Verify file permissions

## Notes

- Files are automatically deleted after 1 hour
- For production use, implement proper authentication
- Consider using HTTPS for secure deployments
- The tool modifies files locally - no data is sent externally 