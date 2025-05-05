# ChromeDriver Downloader

## Description

ChromeDriver Downloader is a powerful and flexible command-line tool for managing and downloading ChromeDriver versions automatically. This tool simplifies the process of obtaining and managing different ChromeDriver versions for Selenium automation testing.

## Key Features

- ✅ Automatic download of specific ChromeDriver versions
- ✅ Support for multiple platforms (Windows and Linux)
- ✅ Support for different architectures (x86 and x64)
- ✅ Listing of available versions with customizable filters
- ✅ Detection and download of missing versions
- ✅ Automatic organization of drivers by major version
- ✅ Support for legacy versions (prior to Chrome 115)

## Download Sources

ChromeDriver Downloader uses two main sources to obtain drivers:

1. **Chrome for Testing API** (versions 115+):
   - URL: `https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json`
   - Provides structured information in JSON format
   - Includes versions from Chrome 115 onwards

2. **Legacy Repository** (versions prior to Chrome 115):
   - URL: `https://chromedriver.storage.googleapis.com/`
   - Provides access to older ChromeDriver versions
   - Includes versions prior to Chrome 115

## Requirements

- Python 3.6 or higher
- Python packages:
  - requests
  - tqdm
  - argparse

## Installation

### Installing Dependencies

```bash
pip install requests tqdm
```

### Cloning the Repository

```bash
git clone https://github.com/JonnathanRiquelmo/chromedriver_downloader.git
cd chromedriver_downloader
```

## Usage

ChromeDriver Downloader offers three main commands:

1. `list` - List available versions
2. `download` - Download a specific version
3. `missing` - Check and download missing versions

### Usage Examples

#### Listing Available Versions

**List all available versions (including legacy):**

```bash
python chromedriver_downloader.py list
```

**List only modern versions (Chrome 115+):**

```bash
python chromedriver_downloader.py list --no-legacy
```

**List versions for Windows:**

```bash
python chromedriver_downloader.py list --platform windows
```

**List specific versions (e.g., Chrome 115):**

```bash
python chromedriver_downloader.py list --version 115
```

**List only x64 versions:**

```bash
python chromedriver_downloader.py list --platform windows --arch x64
```

**List only the latest versions of each major version:**

```bash
python chromedriver_downloader.py list --latest
```

#### Downloading Specific Versions

**Download a specific version:**

```bash
python chromedriver_downloader.py download --platform windows --version 114.0.5735.90
```

**Download to a custom directory:**

```bash
python chromedriver_downloader.py download --platform windows --version 114.0.5735.90 --output C:\selenium\drivers
```

**Download x86 version:**

```bash
python chromedriver_downloader.py download --platform windows --version 114.0.5735.90 --arch x86
```

**Download the latest version of a major version:**

```bash
python chromedriver_downloader.py download --platform windows --version 114 --latest
```

**Download a specific legacy version:**

```bash
python chromedriver_downloader.py download --platform windows --version 85.0.4183.87
```

#### Checking and Downloading Missing Versions

**Check missing versions (including legacy):**

```bash
python chromedriver_downloader.py missing --dir ./drivers --platform windows
```

**Check only modern missing versions:**

```bash
python chromedriver_downloader.py missing --dir ./drivers --platform windows --no-legacy
```

**Check and automatically download missing versions:**

```bash
python chromedriver_downloader.py missing --dir ./drivers --platform windows --download
```

**Check only x64 missing versions:**

```bash
python chromedriver_downloader.py missing --dir ./drivers --platform windows --arch x64
```

**Check only the latest missing versions:**

```bash
python chromedriver_downloader.py missing --dir ./drivers --platform windows --latest
```

#### Download All ChromeDrivers

**Download all ChromeDrivers for Windows x64:**

```bash
# First, list all available versions for Windows x64
python chromedriver_downloader.py list --platform windows --arch x64 > versions.txt

# Then, process the file to extract only the versions
# (This PowerShell command extracts versions from the file)
$versions = Get-Content versions.txt | Select-String -Pattern "Version: ([0-9\.]+)" | ForEach-Object { $_.Matches.Groups[1].Value }

# Download each version
foreach ($version in $versions) {
    python chromedriver_downloader.py download --platform windows --version $version --arch x64 --output ./drivers
}
```

**Download all ChromeDrivers for Linux x64:**

```bash
# On Linux systems, you can use:
python chromedriver_downloader.py list --platform linux --arch x64 | grep "Version:" | sed -E 's/.*Version: ([0-9\.]+).*/\1/' > versions.txt

# Download each version
while read version; do
    python chromedriver_downloader.py download --platform linux --version $version --arch x64 --output ./drivers
done < versions.txt
```

## Directory Structure

After download, drivers are organized in the following structure:

```
drivers/
├── 114.0/
│   ├── chromedriver.exe
│   ├── LICENSE.chromedriver
│   └── ...
├── 115.0/
│   ├── chromedriver.exe
│   ├── LICENSE.chromedriver
│   └── ...
└── ...
```

## Programmatic Usage

In addition to the command-line interface, you can use ChromeDriver Downloader programmatically in your Python scripts:

```python
from chromedriver_downloader import ChromeDriverDownloader

# Initialize the downloader
downloader = ChromeDriverDownloader()

# List available versions (including legacy)
versions = downloader.get_filtered_versions(platform="windows", version_filter="114", arch="x64")

# List only modern versions (without legacy)
modern_versions = downloader.get_filtered_versions(platform="windows", version_filter="114", arch="x64", include_legacy=False)

# Download a specific version
if versions:
    downloader.download_driver(
        download_url=versions[0]["download_url"],
        output_dir="./drivers",
        version=versions[0]["version"],
        is_legacy=versions[0].get("source") == "legacy"
    )

# Check missing versions
missing = downloader.find_missing_drivers("./drivers", "windows", "x64")
for driver_info in missing:
    print(f"Missing version: {driver_info['version_dir']}")
```

## Common Use Cases

### CI/CD Integration

Automate driver downloads in your CI/CD pipelines:

```bash
# Script for CI/CD pipeline
python chromedriver_downloader.py download --platform windows --version 114 --latest --output ./test-drivers
```

### Keeping Drivers Updated

Script to check and download new versions periodically:

```bash
# Add this command to a scheduled job
python chromedriver_downloader.py missing --dir ./drivers --platform windows --download --latest
```

### Support for Multiple Chrome Versions

For projects that need to test on multiple Chrome versions:

```bash
# Download multiple versions
for version in 114 115 116 117 118 119 120; do
    python chromedriver_downloader.py download --platform windows --version $version --latest
done
```

## Troubleshooting

### Error Downloading Drivers

If you encounter errors when downloading drivers, check:

1. Your internet connection
2. If the requested version exists for the specified platform/architecture
3. Write permissions in the output directory

### Version Not Found

If a specific version is not found:

```bash
# Check available versions for a major version
python chromedriver_downloader.py list --version 114
```

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests on the [GitHub repository](https://github.com/JonnathanRiquelmo/chromedriver_downloader).

## License

This project is distributed under the MIT license. See the LICENSE file for more details.

## Acknowledgements

- Google Chrome Team for the Chrome for Testing API
- All contributors and users of this project

---

Developed with ❤️ to make life easier for testers and QAs.