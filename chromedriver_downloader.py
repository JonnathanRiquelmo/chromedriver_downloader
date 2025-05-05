import os
import json
import requests
import sys
import argparse
from tqdm import tqdm
import zipfile
import io
import re
import xml.etree.ElementTree as ET

class ChromeDriverDownloader:
    def __init__(self):
        self.json_url = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"
        self.legacy_url = "https://chromedriver.storage.googleapis.com/"
        self.data = None
        self.legacy_data = None
        self.platform_map = {
            "windows": ["win64", "win32"],  # Added support for win32
            "linux": ["linux64"]
        }
        # Mapping for legacy download URLs
        self.legacy_platform_map = {
            "windows": {
                "x64": "win32",  # In legacy, win32 works for both architectures
                "x86": "win32"
            },
            "linux": {
                "x64": "linux64",
                "x86": "linux32"
            }
        }
    
    def fetch_versions(self):
        """Fetches available versions from Chrome for Testing API"""
        try:
            response = requests.get(self.json_url)
            response.raise_for_status()
            self.data = response.json()
            return True
        except requests.RequestException as e:
            print(f"Error fetching versions: {e}")
            return False
    
    def fetch_legacy_versions(self):
        """Fetches legacy versions available in the old repository"""
        try:
            response = requests.get(self.legacy_url + "?delimiter=/&prefix=")
            response.raise_for_status()
            
            # Parse the returned XML
            root = ET.fromstring(response.content)
            
            # Extract available versions (prefixes ending with /)
            versions = []
            namespace = {'ns': 'http://doc.s3.amazonaws.com/2006-03-01'}
            for prefix in root.findall('.//ns:CommonPrefixes/ns:Prefix', namespace):
                version = prefix.text.strip('/')
                if version and re.match(r'^\d+\.\d+\.\d+\.\d+$', version):
                    versions.append(version)
            
            self.legacy_data = versions
            return True
        except (requests.RequestException, ET.ParseError) as e:
            print(f"Error fetching legacy versions: {e}")
            return False
    
    def get_legacy_download_url(self, version, platform, arch):
        """Generates download URL for legacy versions"""
        platform_key = self.legacy_platform_map.get(platform.lower(), {}).get(arch)
        if not platform_key:
            return None
        
        return f"{self.legacy_url}{version}/chromedriver_{platform_key}.zip"
    
    def get_filtered_versions(self, platform=None, version_filter=None, arch=None, latest_only=False, include_legacy=True):
        """Filters available versions by platform, version and architecture"""
        filtered_versions = []
        
        # Fetch modern versions
        if not self.data:
            if not self.fetch_versions():
                return []
        
        platform_keys = None
        if platform:
            platform_keys = self.platform_map.get(platform.lower())
            if arch:
                # Filter by specific architecture
                if arch == "x64" and platform.lower() == "windows":
                    platform_keys = ["win64"]
                elif arch == "x86" and platform.lower() == "windows":
                    platform_keys = ["win32"]
        
        # Process modern versions
        for version_info in self.data.get("versions", []):
            version = version_info.get("version", "")
            
            # Filter by version if specified
            if version_filter:
                # Extract the major version number (before the first dot)
                major_version = version.split('.')[0]
                if major_version != version_filter:
                    continue
            
            # Check if there are chromedriver downloads available
            downloads = version_info.get("downloads", {}).get("chromedriver", [])
            if not downloads:
                continue
            
            # Filter by platform and architecture if specified
            if platform_keys:
                platform_downloads = [d for d in downloads if d.get("platform") in platform_keys]
                if not platform_downloads:
                    continue
                
                for download in platform_downloads:
                    filtered_versions.append({
                        "version": version,
                        "platform": download.get("platform"),
                        "download_url": download.get("url"),
                        "source": "modern"
                    })
            else:
                # Include all available platforms
                for download in downloads:
                    filtered_versions.append({
                        "version": version,
                        "platform": download.get("platform"),
                        "download_url": download.get("url"),
                        "source": "modern"
                    })
        
        # Fetch legacy versions if requested
        if include_legacy:
            if not self.legacy_data:
                if not self.fetch_legacy_versions():
                    print("Warning: Could not obtain legacy versions.")
                
            if self.legacy_data:
                for version in self.legacy_data:
                    # Filter by version if specified
                    if version_filter:
                        major_version = version.split('.')[0]
                        if major_version != version_filter:
                            continue
                    
                    # For each supported platform/architecture
                    if platform:
                        if arch:
                            # Specific architecture
                            download_url = self.get_legacy_download_url(version, platform, arch)
                            if download_url:
                                platform_key = self.legacy_platform_map[platform.lower()][arch]
                                filtered_versions.append({
                                    "version": version,
                                    "platform": platform_key,
                                    "download_url": download_url,
                                    "source": "legacy"
                                })
                        else:
                            # All architectures for the platform
                            for arch_option in ["x64", "x86"]:
                                download_url = self.get_legacy_download_url(version, platform, arch_option)
                                if download_url:
                                    platform_key = self.legacy_platform_map[platform.lower()][arch_option]
                                    filtered_versions.append({
                                        "version": version,
                                        "platform": platform_key,
                                        "download_url": download_url,
                                        "source": "legacy"
                                    })
                    else:
                        # All platforms and architectures
                        for plat in self.legacy_platform_map:
                            for arch_option in self.legacy_platform_map[plat]:
                                download_url = self.get_legacy_download_url(version, plat, arch_option)
                                if download_url:
                                    platform_key = self.legacy_platform_map[plat][arch_option]
                                    filtered_versions.append({
                                        "version": version,
                                        "platform": platform_key,
                                        "download_url": download_url,
                                        "source": "legacy"
                                    })
        
        # If latest_only is True, return only the latest version of each major version
        if latest_only and filtered_versions:
            # Group versions by major version and platform
            latest_versions = {}
            for version_info in filtered_versions:
                version = version_info["version"]
                platform = version_info["platform"]
                major_version = version.split('.')[0]
                key = f"{major_version}_{platform}"
                
                if key not in latest_versions or self._compare_versions(version, latest_versions[key]["version"]) > 0:
                    latest_versions[key] = version_info
            
            # Convert the dictionary back to a list
            filtered_versions = list(latest_versions.values())
        
        return filtered_versions
    
    def _compare_versions(self, version1, version2):
        """Compares two versions and returns 1 if version1 > version2, -1 if version1 < version2, 0 if equal"""
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = v1_parts[i] if i < len(v1_parts) else 0
            v2 = v2_parts[i] if i < len(v2_parts) else 0
            
            if v1 > v2:
                return 1
            elif v1 < v2:
                return -1
        
        return 0
    
    def list_versions(self, platform=None, version_filter=None, arch=None, latest_only=False, include_legacy=True):
        """Lists available versions with optional filters"""
        versions = self.get_filtered_versions(platform, version_filter, arch, latest_only, include_legacy)
        
        if not versions:
            print("No versions found with the specified filters.")
            return
        
        print(f"Available versions ({len(versions)}):")
        for i, version_info in enumerate(versions, 1):
            platform_str = version_info['platform']
            arch_str = "x64" if platform_str.endswith("64") else "x86"
            source_str = "[Legacy]" if version_info.get('source') == 'legacy' else ""
            print(f"{i}. Version: {version_info['version']} - Platform: {platform_str} ({arch_str}) {source_str}")
        
        return versions
    
    def download_driver(self, download_url, output_dir, version, is_legacy=False):
        """Downloads and extracts the chromedriver"""
        try:
            print(f"Downloading ChromeDriver version {version}...")
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            # Create main output directory if it doesn't exist
            if not os.path.exists(output_dir):
                print(f"Creating output directory: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            
            # Create version directory if it doesn't exist
            major_version = version.split('.')[0]
            output_path = os.path.join(output_dir, f"{major_version}.0")
            os.makedirs(output_path, exist_ok=True)
            
            # Save the zip file temporarily
            temp_zip_path = os.path.join(output_path, "chromedriver_temp.zip")
            with open(temp_zip_path, 'wb') as f:
                f.write(response.content)
            
            # Extract the zip file to a temporary directory
            temp_extract_dir = os.path.join(output_path, "temp_extract")
            os.makedirs(temp_extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)
            
            # Process differently depending on whether it's legacy or modern
            if is_legacy:
                # Legacy versions have the chromedriver directly in the root of the zip
                source_dir = temp_extract_dir
            else:
                # Move files from the chromedriver directory to the destination directory
                chromedriver_dir = os.path.join(temp_extract_dir, "chromedriver-win64")
                if not os.path.exists(chromedriver_dir):
                    # Try other common directory name variations
                    possible_dirs = [
                        os.path.join(temp_extract_dir, "chromedriver-win32"),
                        os.path.join(temp_extract_dir, "chromedriver"),
                        os.path.join(temp_extract_dir, "chromedriver-linux64")
                    ]
                    for dir_path in possible_dirs:
                        if os.path.exists(dir_path):
                            chromedriver_dir = dir_path
                            break
                
                source_dir = chromedriver_dir if os.path.exists(chromedriver_dir) else temp_extract_dir
            
            # Copy files to the destination directory
            if os.path.exists(source_dir):
                # Move all files from the source directory to the destination directory
                for item in os.listdir(source_dir):
                    item_path = os.path.join(source_dir, item)
                    dest_path = os.path.join(output_path, item)
                    
                    # If the destination already exists, remove it first
                    if os.path.exists(dest_path):
                        if os.path.isdir(dest_path):
                            import shutil
                            shutil.rmtree(dest_path)
                        else:
                            os.remove(dest_path)
                    
                    # Move the file/directory
                    if os.path.isdir(item_path):
                        import shutil
                        shutil.copytree(item_path, dest_path)
                    else:
                        import shutil
                        shutil.copy2(item_path, dest_path)
            
            # Clean up temporary files
            import shutil
            if os.path.exists(temp_zip_path):
                os.remove(temp_zip_path)
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
            
            print(f"ChromeDriver downloaded and extracted successfully to: {output_path}")
            return True
        except Exception as e:
            print(f"Error downloading or extracting driver: {e}")
            return False
    
    def find_missing_drivers(self, drivers_dir, platform, arch=None, latest_only=False, include_legacy=True):
        """Identifies missing drivers by comparing with those available online"""
        # Create the directory if it doesn't exist
        if not os.path.isdir(drivers_dir):
            print(f"Directory {drivers_dir} does not exist. Creating directory...")
            os.makedirs(drivers_dir, exist_ok=True)
        
        # Get all available versions for the platform and architecture
        all_versions = self.get_filtered_versions(platform, None, arch, latest_only, include_legacy)
        if not all_versions:
            print("Could not obtain the list of available versions.")
            return []
        
        # Map major versions to download URLs
        version_map = {}
        for version_info in all_versions:
            major_version = version_info["version"].split('.')[0]
            version_map[f"{major_version}.0"] = {
                "full_version": version_info["version"],
                "download_url": version_info["download_url"],
                "is_legacy": version_info.get("source") == "legacy"
            }
        
        # List existing directories
        existing_dirs = [d for d in os.listdir(drivers_dir) 
                         if os.path.isdir(os.path.join(drivers_dir, d))]
        
        # Find missing versions
        missing_versions = []
        for version_dir, info in version_map.items():
            if version_dir not in existing_dirs:
                missing_versions.append({
                    "version_dir": version_dir,
                    "full_version": info["full_version"],
                    "download_url": info["download_url"],
                    "is_legacy": info["is_legacy"]
                })
        
        return missing_versions

def main():
    parser = argparse.ArgumentParser(description="Download Manager for ChromeDriver")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Command to list versions
    list_parser = subparsers.add_parser("list", help="List available versions")
    list_parser.add_argument("--platform", choices=["windows", "linux"], 
                            help="Filter by platform (windows or linux)")
    list_parser.add_argument("--version", help="Filter by version (e.g., '114')")
    list_parser.add_argument("--arch", choices=["x86", "x64"],
                            help="Filter by architecture (x86 or x64)")
    list_parser.add_argument("--latest", action="store_true",
                            help="Return only the latest version of each major version")
    list_parser.add_argument("--no-legacy", action="store_true",
                            help="Do not include legacy chromedriver versions")
    
    # Command to download a specific version
    download_parser = subparsers.add_parser("download", help="Download a specific version")
    download_parser.add_argument("--platform", choices=["windows", "linux"], required=True,
                               help="Platform (windows or linux)")
    download_parser.add_argument("--version", required=True, 
                               help="Version to download (e.g., '114.0.5735.90')")
    download_parser.add_argument("--output", default="./drivers",
                               help="Output directory (default: ./drivers)")
    download_parser.add_argument("--arch", choices=["x86", "x64"], default="x64",
                               help="Architecture (x86 or x64, default: x64)")
    download_parser.add_argument("--latest", action="store_true",
                               help="Download only the latest version if the specified version is a major version")
    download_parser.add_argument("--no-legacy", action="store_true",
                               help="Do not include legacy chromedriver versions")
    
    # Command to check for missing drivers
    missing_parser = subparsers.add_parser("missing", help="Check for missing drivers")
    missing_parser.add_argument("--dir", required=True,
                              help="Directory containing existing drivers")
    missing_parser.add_argument("--platform", choices=["windows", "linux"], required=True,
                              help="Platform (windows or linux)")
    missing_parser.add_argument("--download", action="store_true",
                              help="Automatically download missing drivers")
    missing_parser.add_argument("--arch", choices=["x86", "x64"], default="x64",
                              help="Architecture (x86 or x64, default: x64)")
    missing_parser.add_argument("--latest", action="store_true",
                              help="Consider only the latest versions of each major version")
    missing_parser.add_argument("--no-legacy", action="store_true",
                              help="Do not include legacy chromedriver versions")
    
    args = parser.parse_args()
    
    downloader = ChromeDriverDownloader()
    
    # Determine whether to include legacy versions
    include_legacy = not getattr(args, 'no_legacy', False)
    
    if args.command == "list":
        downloader.list_versions(args.platform, args.version, args.arch, args.latest, include_legacy)
    
    elif args.command == "download":
        # Update to use architecture and latest parameters
        arch = args.arch
        latest_only = args.latest
        
        # If latest_only is True and the version is just a major number, get the latest version
        if latest_only and args.version and args.version.isdigit():
            versions = downloader.get_filtered_versions(
                platform=args.platform, 
                version_filter=args.version,
                arch=arch,
                latest_only=True,
                include_legacy=include_legacy
            )
            
            if versions:
                # Use the first (and only) version that matches
                version_info = versions[0]
                print(f"Using latest version: {version_info['version']}")
                downloader.download_driver(
                    download_url=version_info["download_url"],
                    output_dir=args.output,
                    version=version_info["version"],
                    is_legacy=version_info.get("source") == "legacy"
                )
            else:
                print(f"No version found matching: {args.version}")
        else:
            # Try to find an exact match for the specified version
            versions = downloader.get_filtered_versions(
                platform=args.platform,
                arch=arch,
                include_legacy=include_legacy
            )
            
            # Filter for exact version match
            matching_versions = [v for v in versions if v["version"] == args.version]
            
            if matching_versions:
                version_info = matching_versions[0]
                downloader.download_driver(
                    download_url=version_info["download_url"],
                    output_dir=args.output,
                    version=version_info["version"],
                    is_legacy=version_info.get("source") == "legacy"
                )
            else:
                print(f"Version {args.version} not found for platform {args.platform} and architecture {arch}")
    
    elif args.command == "missing":
        # Find missing drivers
        missing = downloader.find_missing_drivers(
            args.dir, 
            args.platform, 
            args.arch, 
            args.latest, 
            include_legacy
        )
        
        if not missing:
            print("No missing drivers found.")
            return
        
        print(f"Found {len(missing)} missing drivers:")
        for i, driver_info in enumerate(missing, 1):
            print(f"{i}. {driver_info['version_dir']} (Full version: {driver_info['full_version']})")
        
        # Download missing drivers if requested
        if args.download and missing:
            print("\nDownloading missing drivers...")
            for driver_info in missing:
                print(f"\nProcessing {driver_info['version_dir']} (Full version: {driver_info['full_version']})")
                downloader.download_driver(
                    download_url=driver_info["download_url"],
                    output_dir=args.dir,
                    version=driver_info["full_version"],
                    is_legacy=driver_info["is_legacy"]
                )
    else:
        parser.print_help()

if __name__ == "__main__":
    main()