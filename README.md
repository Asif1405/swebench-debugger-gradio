# JavaScript Test Harness Debugger with Gradio

A powerful web-based tool for building and running JavaScript test suites in isolated Docker environments. This tool provides a user-friendly Gradio interface for setting up containerized testing environments, executing tests, and parsing test output from various JavaScript testing frameworks.

## 🚀 Features

- **Docker-based Test Environment**: Builds isolated test environments with configurable Node.js versions
- **Multi-Framework Support**: Parse test outputs from various JavaScript testing frameworks:
  - Jest
  - Vitest
  - Mocha
  - Karma
  - TAP
  - Chart.js
  - React PDF
  - p5.js
  - Calypso
  - Marked
- **Git Integration**: Clone and test specific commits from GitHub repositories
- **Real-time Streaming**: Watch build and test execution in real-time
- **Web Interface**: Easy-to-use Gradio web interface
- **Flexible Configuration**: JSON-based configuration for build and test commands

## 📋 Prerequisites

- **Docker**: Required for building and running test environments
- **Python 3.11+**: For running the Gradio application
- **Git**: For cloning repositories (handled within Docker containers)

## 🛠️ Installation

### Local Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd harness-debugger-gradio
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python app.py
   ```

4. **Access the web interface**:
   Open http://localhost:7860 in your browser

### Docker Setup

1. **Using Docker Compose** (Recommended):
   ```bash
   docker-compose up -d
   ```
   Access the application at http://localhost:5151

2. **Using Docker directly**:
   ```bash
   docker build -t harness-debugger .
   docker run -p 7860:7860 -v /var/run/docker.sock:/var/run/docker.sock harness-debugger
   ```

## 📖 Usage

### 1. Configure Repository Specifications

Create a JSON configuration with the following structure:

```json
{
  "docker_specs": {
    "node_version": "18"
  },
  "pre_install": [
    "npm config set registry https://registry.npmjs.org/"
  ],
  "install": [
    "npm install"
  ],
  "build": [
    "npm run build"
  ],
  "test_cmd": "npm test"
}
```

### 2. Build Test Environment

1. Fill in the **Repo Specs JSON** with your configuration
2. Enter the **Git Repo URL** (e.g., `https://github.com/username/repo.git`)
3. Specify **Base Commit SHA** and **Head Commit SHA**
4. Choose which commit to build (base or head)
5. Set the **Docker executable command** (usually `docker` or `sudo docker`)
6. Click **🔨 Build Image**

The system will:
- Create a Docker image with the specified Node.js version
- Clone the repository and checkout the specified commit
- Run pre-install, install, and build commands
- Install necessary dependencies (Chrome, Python, etc.)

### 3. Run Tests

1. Ensure you have a built test image
2. Enter test file paths in the **Raw Log to Parse** field (space-separated)
3. Click **🧪 Run Tests**

### 4. Parse Test Logs

1. Select the appropriate **Log Parser** for your testing framework
2. Paste raw test logs into the **Raw Log to Parse** field
3. Click **🔍 Parse Logs**

The parser will extract test results and format them as JSON with test names and their status (PASSED, FAILED, SKIPPED, PENDING).

## 🏗️ Architecture

### Core Components

- **`app.py`**: Main Gradio application with web interface
- **Log Parsers**: Framework-specific parsers for extracting test results
- **Docker Builder**: Creates isolated test environments
- **Test Runner**: Executes tests in Docker containers

### Supported Test Frameworks

| Framework | Parser Function | Description |
|-----------|----------------|-------------|
| Jest | `parse_log_jest` | Popular JavaScript testing framework |
| Vitest | `parse_log_vitest` | Fast Vite-native testing framework |
| Mocha | `parse_log_mocha_v2` | Flexible JavaScript test framework |
| Karma | `parse_log_karma` | Test runner for browsers |
| TAP | `parse_log_tap` | Test Anything Protocol |
| Chart.js | `parse_log_chart_js` | Chart.js specific test parser |
| React PDF | `parse_log_react_pdf` | React PDF library tests |
| p5.js | `parse_log_p5js` | p5.js creative coding library |
| Calypso | `parse_log_calypso` | WordPress.com Calypso tests |
| Marked | `parse_log_marked` | Markdown parser tests |

## 🔧 Configuration

### Environment Variables

- `GRADIO_SERVER_PORT`: Port for the Gradio server (default: 7860)

### Docker Configuration

The application requires Docker socket access to build and run test containers. When using Docker Compose, this is handled automatically.

### JSON Specification Format

```json
{
  "docker_specs": {
    "node_version": "16|18|20"  // Required: Node.js version
  },
  "pre_install": [              // Optional: Commands before npm install
    "command1",
    "command2"
  ],
  "install": [                  // Optional: Installation commands
    "npm install",
    "npm ci"
  ],
  "build": [                    // Optional: Build commands
    "npm run build",
    "npm run compile"
  ],
  "test_cmd": "npm test"        // Required: Test execution command
}
```

## 🐛 Troubleshooting

### Common Issues

1. **Docker permission denied**:
   - Ensure Docker socket is accessible
   - Try using `sudo docker` in the Docker executable field
   - Verify Docker daemon is running

2. **Build failures**:
   - Check Node.js version compatibility
   - Verify repository URL is accessible
   - Ensure commit SHAs are valid

3. **Test parsing issues**:
   - Select the correct parser for your testing framework
   - Verify log format matches expected patterns
   - Check for ANSI color codes that might interfere

### Debug Mode

Set the `GRADIO_DEBUG` environment variable to enable detailed logging:

```bash
export GRADIO_DEBUG=1
python app.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new parsers or functionality
4. Submit a pull request

### Adding New Parsers

To add support for a new testing framework:

1. Implement a parser function in `app.py`:
   ```python
   def parse_log_framework_name(log: str) -> Dict[str,str]:
       # Parse log and return {test_name: status} mapping
       pass
   ```

2. Add the parser to the `get_js_parser_by_name` function

3. Update the dropdown choices in the Gradio interface

## 📄 License

This project is open source. Please refer to the LICENSE file for details.

## 🔗 Related Projects

- [Gradio](https://gradio.app/) - Web interface framework
- [Docker](https://docker.com/) - Containerization platform
- [Jest](https://jestjs.io/) - JavaScript testing framework
- [Vitest](https://vitest.dev/) - Fast testing framework

---

**Note**: This tool is designed for development and testing purposes. Ensure proper security measures when running in production environments.
