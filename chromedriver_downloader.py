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
            "windows": ["win64", "win32"],  # Adicionado suporte para win32
            "linux": ["linux64"]
        }
        # Mapeamento para URLs de download legados
        self.legacy_platform_map = {
            "windows": {
                "x64": "win32",  # No legado, win32 funciona para ambas arquiteturas
                "x86": "win32"
            },
            "linux": {
                "x64": "linux64",
                "x86": "linux32"
            }
        }
    
    def fetch_versions(self):
        """Busca as versoes disponiveis da API do Chrome for Testing"""
        try:
            response = requests.get(self.json_url)
            response.raise_for_status()
            self.data = response.json()
            return True
        except requests.RequestException as e:
            print(f"Erro ao buscar versoes: {e}")
            return False
    
    def fetch_legacy_versions(self):
        """Busca as versoes legadas disponÃ­veis no repositÃ³rio antigo"""
        try:
            response = requests.get(self.legacy_url + "?delimiter=/&prefix=")
            response.raise_for_status()
            
            # Analisar o XML retornado
            root = ET.fromstring(response.content)
            
            # Extrair as versÃµes disponÃ­veis (prefixos que terminam com /)
            versions = []
            namespace = {'ns': 'http://doc.s3.amazonaws.com/2006-03-01'}
            for prefix in root.findall('.//ns:CommonPrefixes/ns:Prefix', namespace):
                version = prefix.text.strip('/')
                if version and re.match(r'^\d+\.\d+\.\d+\.\d+$', version):
                    versions.append(version)
            
            self.legacy_data = versions
            return True
        except (requests.RequestException, ET.ParseError) as e:
            print(f"Erro ao buscar versoes legadas: {e}")
            return False
    
    def get_legacy_download_url(self, version, platform, arch):
        """Gera a URL de download para versÃµes legadas"""
        platform_key = self.legacy_platform_map.get(platform.lower(), {}).get(arch)
        if not platform_key:
            return None
        
        return f"{self.legacy_url}{version}/chromedriver_{platform_key}.zip"
    
    def get_filtered_versions(self, platform=None, version_filter=None, arch=None, latest_only=False, include_legacy=True):
        """Filtra as versoes disponiveis por plataforma, versao e arquitetura"""
        filtered_versions = []
        
        # Buscar versÃµes modernas
        if not self.data:
            if not self.fetch_versions():
                return []
        
        platform_keys = None
        if platform:
            platform_keys = self.platform_map.get(platform.lower())
            if arch:
                # Filtrar por arquitetura especÃ­fica
                if arch == "x64" and platform.lower() == "windows":
                    platform_keys = ["win64"]
                elif arch == "x86" and platform.lower() == "windows":
                    platform_keys = ["win32"]
        
        # Processar versÃµes modernas
        for version_info in self.data.get("versions", []):
            version = version_info.get("version", "")
            
            # Filtrar por versao se especificado
            if version_filter:
                # Extrair o nÃºmero principal da versÃ£o (antes do primeiro ponto)
                major_version = version.split('.')[0]
                if major_version != version_filter:
                    continue
            
            # Verificar se hÃ¡ downloads de chromedriver disponiveis
            downloads = version_info.get("downloads", {}).get("chromedriver", [])
            if not downloads:
                continue
            
            # Filtrar por plataforma e arquitetura se especificado
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
                # Incluir todas as plataformas disponiveis
                for download in downloads:
                    filtered_versions.append({
                        "version": version,
                        "platform": download.get("platform"),
                        "download_url": download.get("url"),
                        "source": "modern"
                    })
        
        # Buscar versÃµes legadas se solicitado
        if include_legacy:
            if not self.legacy_data:
                if not self.fetch_legacy_versions():
                    print("Aviso: NÃ£o foi possÃ­vel obter versÃµes legadas.")
                
            if self.legacy_data:
                for version in self.legacy_data:
                    # Filtrar por versao se especificado
                    if version_filter:
                        major_version = version.split('.')[0]
                        if major_version != version_filter:
                            continue
                    
                    # Para cada plataforma/arquitetura suportada
                    if platform:
                        if arch:
                            # Arquitetura especÃ­fica
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
                            # Todas as arquiteturas para a plataforma
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
                        # Todas as plataformas e arquiteturas
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
        
        # Se latest_only for True, retorna apenas a versÃ£o mais recente de cada versÃ£o principal
        if latest_only and filtered_versions:
            # Agrupar versÃµes por versÃ£o principal e plataforma
            latest_versions = {}
            for version_info in filtered_versions:
                version = version_info["version"]
                platform = version_info["platform"]
                major_version = version.split('.')[0]
                key = f"{major_version}_{platform}"
                
                if key not in latest_versions or self._compare_versions(version, latest_versions[key]["version"]) > 0:
                    latest_versions[key] = version_info
            
            # Converter o dicionÃ¡rio de volta para uma lista
            filtered_versions = list(latest_versions.values())
        
        return filtered_versions
    
    def _compare_versions(self, version1, version2):
        """Compara duas versÃµes e retorna 1 se version1 > version2, -1 se version1 < version2, 0 se iguais"""
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
        """Lista as versoes disponiveis com filtros opcionais"""
        versions = self.get_filtered_versions(platform, version_filter, arch, latest_only, include_legacy)
        
        if not versions:
            print("Nenhuma versao encontrada com os filtros especificados.")
            return
        
        print(f"Versoes disponiveis ({len(versions)}):")
        for i, version_info in enumerate(versions, 1):
            platform_str = version_info['platform']
            arch_str = "x64" if platform_str.endswith("64") else "x86"
            source_str = "[Legado]" if version_info.get('source') == 'legacy' else ""
            print(f"{i}. Versao: {version_info['version']} - Plataforma: {platform_str} ({arch_str}) {source_str}")
        
        return versions
    
    def download_driver(self, download_url, output_dir, version, is_legacy=False):
        """Faz o download e extrai o chromedriver"""
        try:
            print(f"Baixando ChromeDriver versao {version}...")
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            # Criar diretorio de saÃ­da principal se nao existir
            if not os.path.exists(output_dir):
                print(f"Criando diretorio de saida: {output_dir}")
                os.makedirs(output_dir, exist_ok=True)
            
            # Criar diretorio de versÃ£o se nao existir
            major_version = version.split('.')[0]
            output_path = os.path.join(output_dir, f"{major_version}.0")
            os.makedirs(output_path, exist_ok=True)
            
            # Salvar o arquivo zip temporariamente
            temp_zip_path = os.path.join(output_path, "chromedriver_temp.zip")
            with open(temp_zip_path, 'wb') as f:
                f.write(response.content)
            
            # Extrair o arquivo zip para um diretÃ³rio temporÃ¡rio
            temp_extract_dir = os.path.join(output_path, "temp_extract")
            os.makedirs(temp_extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)
            
            # Processar diferentemente dependendo se Ã© legado ou moderno
            if is_legacy:
                # VersÃµes legadas tÃªm o chromedriver diretamente na raiz do zip
                source_dir = temp_extract_dir
            else:
                # Mover os arquivos do diretÃ³rio chromedriver para o diretÃ³rio de destino
                chromedriver_dir = os.path.join(temp_extract_dir, "chromedriver-win64")
                if not os.path.exists(chromedriver_dir):
                    # Tentar outras variaÃ§Ãµes comuns do nome do diretÃ³rio
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
            
            # Copiar os arquivos para o diretÃ³rio de destino
            if os.path.exists(source_dir):
                # Mover todos os arquivos do diretÃ³rio fonte para o diretÃ³rio de destino
                for item in os.listdir(source_dir):
                    item_path = os.path.join(source_dir, item)
                    dest_path = os.path.join(output_path, item)
                    
                    # Se o destino jÃ¡ existir, remover primeiro
                    if os.path.exists(dest_path):
                        if os.path.isdir(dest_path):
                            import shutil
                            shutil.rmtree(dest_path)
                        else:
                            os.remove(dest_path)
                    
                    # Mover o arquivo/diretÃ³rio
                    if os.path.isdir(item_path):
                        import shutil
                        shutil.copytree(item_path, dest_path)
                    else:
                        import shutil
                        shutil.copy2(item_path, dest_path)
            
            # Limpar arquivos temporÃ¡rios
            import shutil
            if os.path.exists(temp_zip_path):
                os.remove(temp_zip_path)
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
            
            print(f"ChromeDriver baixado e extraido com sucesso em: {output_path}")
            return True
        except Exception as e:
            print(f"Erro ao baixar ou extrair o driver: {e}")
            return False
    
    def find_missing_drivers(self, drivers_dir, platform, arch=None, latest_only=False, include_legacy=True):
        """Identifica drivers faltantes comparando com os disponiveis online"""
        # Criar o diretÃ³rio se nÃ£o existir
        if not os.path.isdir(drivers_dir):
            print(f"O diretorio {drivers_dir} nao existe. Criando diretorio...")
            os.makedirs(drivers_dir, exist_ok=True)
        
        # Obter todas as versoes disponiveis para a plataforma e arquitetura
        all_versions = self.get_filtered_versions(platform, None, arch, latest_only, include_legacy)
        if not all_versions:
            print("Nao foi possivel obter a lista de versoes disponiveis.")
            return []
        
        # Mapear versoes principais para URLs de download
        version_map = {}
        for version_info in all_versions:
            major_version = version_info["version"].split('.')[0]
            version_map[f"{major_version}.0"] = {
                "full_version": version_info["version"],
                "download_url": version_info["download_url"],
                "is_legacy": version_info.get("source") == "legacy"
            }
        
        # Listar diretorios existentes
        existing_dirs = [d for d in os.listdir(drivers_dir) 
                         if os.path.isdir(os.path.join(drivers_dir, d))]
        
        # Encontrar versoes faltantes
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
    parser = argparse.ArgumentParser(description="Gerenciador de download para ChromeDriver")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponiveis")
    
    # Comando para listar versoes
    list_parser = subparsers.add_parser("list", help="Listar versoes disponiveis")
    list_parser.add_argument("--platform", choices=["windows", "linux"], 
                            help="Filtrar por plataforma (windows ou linux)")
    list_parser.add_argument("--version", help="Filtrar por versao (ex: '114')")
    list_parser.add_argument("--arch", choices=["x86", "x64"],
                            help="Filtrar por arquitetura (x86 ou x64)")
    list_parser.add_argument("--latest", action="store_true",
                            help="Retornar apenas a versÃ£o mais recente de cada versÃ£o principal")
    list_parser.add_argument("--no-legacy", action="store_true",
                            help="NÃ£o incluir versÃµes legadas do chromedriver")
    
    # Comando para baixar uma versao especifica
    download_parser = subparsers.add_parser("download", help="Baixar uma versao especifica")
    download_parser.add_argument("--platform", choices=["windows", "linux"], required=True,
                               help="Plataforma (windows ou linux)")
    download_parser.add_argument("--version", required=True, 
                               help="versao a ser baixada (ex: '114.0.5735.90')")
    download_parser.add_argument("--output", default="./drivers",
                               help="diretorio de saida (padrao: ./drivers)")
    download_parser.add_argument("--arch", choices=["x86", "x64"], default="x64",
                               help="Arquitetura (x86 ou x64, padrao: x64)")
    download_parser.add_argument("--latest", action="store_true",
                               help="Baixar apenas a versÃ£o mais recente se a versÃ£o especificada for uma versÃ£o principal")
    download_parser.add_argument("--no-legacy", action="store_true",
                               help="NÃ£o incluir versÃµes legadas do chromedriver")
    
    # Comando para verificar drivers faltantes
    missing_parser = subparsers.add_parser("missing", help="Verificar drivers faltantes")
    missing_parser.add_argument("--dir", required=True,
                              help="diretorio contendo os drivers existentes")
    missing_parser.add_argument("--platform", choices=["windows", "linux"], required=True,
                              help="Plataforma (windows ou linux)")
    missing_parser.add_argument("--download", action="store_true",
                              help="Baixar automaticamente os drivers faltantes")
    missing_parser.add_argument("--arch", choices=["x86", "x64"], default="x64",
                              help="Arquitetura (x86 ou x64, padrao: x64)")
    missing_parser.add_argument("--latest", action="store_true",
                              help="Considerar apenas as versÃµes mais recentes de cada versÃ£o principal")
    missing_parser.add_argument("--no-legacy", action="store_true",
                              help="NÃ£o incluir versÃµes legadas do chromedriver")
    
    args = parser.parse_args()
    
    downloader = ChromeDriverDownloader()
    
    # Determinar se deve incluir versÃµes legadas
    include_legacy = not getattr(args, 'no_legacy', False)
    
    if args.command == "list":
        downloader.list_versions(args.platform, args.version, args.arch, args.latest, include_legacy)
    
    elif args.command == "download":
        # Atualizar para usar o parÃ¢metro de arquitetura e latest
        arch = args.arch
        latest_only = args.latest
        
        # Se latest_only for True e a versÃ£o for apenas um nÃºmero principal (ex: "114"),
        # buscar apenas a versÃ£o mais recente dessa versÃ£o principal
        if latest_only and args.version and args.version.isdigit():
            versions = downloader.get_filtered_versions(args.platform, args.version, arch, True, include_legacy)
            if versions:
                version_info = versions[0]  # Pega a primeira (e Ãºnica) versÃ£o mais recente
                is_legacy = version_info.get("source") == "legacy"
                print(f"Baixando a versÃ£o mais recente do ChromeDriver {args.version}: {version_info['version']} {'(Legado)' if is_legacy else ''}")
                downloader.download_driver(version_info["download_url"], args.output, version_info["version"], is_legacy)
                return
        
        # Caso contrÃ¡rio, continua com o comportamento normal
        versions = downloader.get_filtered_versions(args.platform, args.version, arch, False, include_legacy)
        if not versions:
            print(f"Versao {args.version} nao encontrada para a plataforma {args.platform} ({arch}).")
            return
        
        # Encontrar a correspondencia exata ou a mais proxima
        exact_match = None
        for version_info in versions:
            if version_info["version"] == args.version:
                exact_match = version_info
                break
        
        if exact_match:
            is_legacy = exact_match.get("source") == "legacy"
            downloader.download_driver(exact_match["download_url"], args.output, args.version, is_legacy)
        else:
            print(f"versao exata {args.version} nao encontrada. versoes disponiveis:")
            for i, version_info in enumerate(versions[:5], 1):
                source_str = "(Legado)" if version_info.get("source") == "legacy" else ""
                print(f"{i}. {version_info['version']} {source_str}")
            
            choice = input("Selecione uma versao para baixar (nÃºmero) ou 'q' para sair: ")
            if choice.lower() != 'q' and choice.isdigit() and 1 <= int(choice) <= len(versions):
                selected = versions[int(choice) - 1]
                is_legacy = selected.get("source") == "legacy"
                downloader.download_driver(selected["download_url"], args.output, selected["version"], is_legacy)
    
    elif args.command == "missing":
        # Atualizar para usar o parÃ¢metro de arquitetura e latest
        arch = args.arch
        latest_only = args.latest
        missing = downloader.find_missing_drivers(args.dir, args.platform, arch, latest_only, include_legacy)
        
        if not missing:
            print("nao ha drivers faltantes.")
            return
        
        print(f"Drivers faltantes ({len(missing)}):")
        for i, driver_info in enumerate(missing, 1):
            legacy_str = "(Legado)" if driver_info.get("is_legacy") else ""
            print(f"{i}. versao: {driver_info['version_dir']} (completa: {driver_info['full_version']}) {legacy_str}")
        
        if args.download:
            print("\nBaixando drivers faltantes...")
            for driver_info in missing:
                downloader.download_driver(
                    driver_info["download_url"], 
                    args.dir, 
                    driver_info["full_version"],
                    driver_info.get("is_legacy", False)
                )
        else:
            print("\nUse a opcao --download para baixar automaticamente os drivers faltantes.")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()