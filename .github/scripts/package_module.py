#!/usr/bin/env python3
import os
import toml
import argparse
import datetime
import zipfile
import glob
import json
import re
import shutil
import subprocess
import platform
import sys
import hashlib
from pathlib import Path

def extract_latest_changelog(changelog_file):
    """从 CHANGELOG.MD 文件中提取最新版本的更新日志"""
    try:
        with open(changelog_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找最新版本的部分
        latest_version_match = re.search(r'## \[(.*?)\].*?\n(.*?)(?=\n## \[|$)', content, re.DOTALL)
        if latest_version_match:
            version = latest_version_match.group(1)
            changelog = latest_version_match.group(2).strip()
            return changelog
        return None
    except Exception as e:
        print(f"读取 CHANGELOG.MD 时出错: {e}")
        return None

def calculate_file_hash(filename, hash_type="sha256"):
    """计算文件的哈希值"""
    hash_func = hashlib.new(hash_type)
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()

def create_executable(module_id, target_platform, target_arch=None):
    """为指定平台创建可执行文件"""
    bin_dir = "bin"
    os.makedirs(bin_dir, exist_ok=True)
    
    # 准备构建命令
    pyinstaller_cmd = ["pyinstaller", "--onefile"]
    entry_point = f"{module_id}.py"
    
    # 为不同平台设置输出文件名
    if target_platform == "windows":
        exe_name = f"{module_id}.exe"
        if target_arch:
            exe_name = f"{module_id}-{target_arch}.exe"
    else:
        exe_name = f"{module_id}"
        if target_arch:
            exe_name = f"{module_id}-{target_platform}-{target_arch}"
    
    # 添加目标平台和架构选项
    if target_platform != platform.system().lower() or target_arch:
        pyinstaller_cmd.append("--target-platform")
        pyinstaller_cmd.append(target_platform)
        
    if target_arch:
        pyinstaller_cmd.append("--target-arch")
        pyinstaller_cmd.append(target_arch)
    
    # 设置输出目录和文件名
    pyinstaller_cmd.extend(["-n", exe_name, "--distpath", bin_dir, entry_point])
    
    # 尝试运行构建
    try:
        print(f"正在为 {target_platform} {target_arch or ''} 构建可执行文件...")
        subprocess.run(pyinstaller_cmd, check=True, capture_output=True)
        print(f"构建成功: {os.path.join(bin_dir, exe_name)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {e}")
        print(f"错误输出: {e.stderr.decode('utf-8')}")
        return False
    except Exception as e:
        print(f"构建过程中出现异常: {e}")
        return False

def refresh_dependencies():
    """使用 uv sync 刷新依赖"""
    try:
        print("刷新依赖...")
        result = subprocess.run(["uv", "sync"], check=True, capture_output=True, text=True)
        print("依赖刷新成功!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"依赖刷新失败: {e}")
        print(f"错误输出: {e.stderr}")
        return False
    except FileNotFoundError:
        print("错误: 未找到 uv 命令。请确保已安装 uv 并添加到 PATH 中。")
        print("尝试安装 uv: pip install uv")
        return False

def find_license_files():
    """查找项目中的许可证文件"""
    license_patterns = [
        'LICENSE*', 'License*', 'license*', 
        'COPYING*', 'Copying*', 'copying*',
        'COPYRIGHT*', 'Copyright*', 'copyright*'
    ]
    
    license_files = []
    for pattern in license_patterns:
        license_files.extend(glob.glob(pattern))
    
    if license_files:
        print(f"找到许可证相关文件: {', '.join(license_files)}")
    else:
        print("未找到许可证文件，仅使用 meta.toml 中的许可证类型信息")
    
    return license_files

def main():
    parser = argparse.ArgumentParser(description='Package AIVK module')
    parser.add_argument('--version', required=True, help='New version number')
    parser.add_argument('--changelog', help='Changelog for this version (可选，留空将使用 CHANGELOG.MD)')
    parser.add_argument('--skip-executables', action='store_true', help='跳过构建可执行文件')
    parser.add_argument('--skip-dependencies', action='store_true', help='跳过刷新依赖')
    args = parser.parse_args()
    
    # 读取 meta.toml
    meta_path = 'meta.toml'
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta_data = toml.load(f)
    
    # 获取模块 ID
    module_id = meta_data.get('id')
    if not module_id:
        raise ValueError("未在 meta.toml 中找到模块 ID")
    
    # 更新 meta.toml 版本信息
    meta_data['version'] = args.version
    
    # 生成新的版本代号 (年月日序列)
    now = datetime.datetime.now()
    sequence = 1
    # 如果同一天发布多个版本，增加序列号
    if meta_data.get('versionCode'):
        date_part = int(str(meta_data['versionCode'])[:-2])
        today_date = int(f"{now.year % 100}{now.month:02d}{now.day:02d}")
        if date_part == today_date:
            sequence = (meta_data['versionCode'] % 100) + 1
    
    version_code = int(f"{now.year % 100}{now.month:02d}{now.day:02d}{sequence:02d}")
    meta_data['versionCode'] = version_code
    
    # 写回 meta.toml
    with open(meta_path, 'w', encoding='utf-8') as f:
        toml.dump(meta_data, f)
    
    # 刷新依赖
    if not args.skip_dependencies:
        refresh_dependencies()
    
    # 构建可执行文件
    if not args.skip_executables:
        # 安装 PyInstaller
        try:
            subprocess.run(["pip", "install", "pyinstaller"], check=True)
            print("PyInstaller 安装成功!")
        except subprocess.CalledProcessError as e:
            print(f"PyInstaller 安装失败: {e}")
            print("继续打包过程...")
        
        # 为各个平台和架构构建可执行文件
        platforms_archs = [
            ("windows", None),  # 默认架构 (当前系统)
            ("windows", "x86_64"),
            ("windows", "x86"),
            ("linux", None),    # 默认架构 (当前系统)
            ("linux", "x86_64"),
            ("linux", "aarch64"),
            ("darwin", None),   # 默认架构 (当前系统)
            ("darwin", "x86_64"),
            ("darwin", "arm64")
        ]
        
        for platform_name, arch in platforms_archs:
            create_executable(module_id, platform_name, arch)
    
    # 查找许可证文件
    license_files = find_license_files()
    
    # 准备打包文件列表 - 按新标准包含指定文件和目录
    files_to_package = [
        # 必需的配置和元数据文件
        'meta.toml',
        'config.toml' if os.path.exists('config.toml') else None,
        'pyproject.toml' if os.path.exists('pyproject.toml') else None,
        
        # 主模块文件 (id.py)
        f"{module_id}.py" if os.path.exists(f"{module_id}.py") else None,
        
        # 文档文件
        'README.md' if os.path.exists('README.md') else None,
        'README.MD' if os.path.exists('README.MD') else None,
        'CHANGELOG.md' if os.path.exists('CHANGELOG.md') else None,
        'CHANGELOG.MD' if os.path.exists('CHANGELOG.MD') else None,
        
        # Python 版本信息
        '.python-version' if os.path.exists('.python-version') else None
    ]
    
    # 添加许可证文件
    files_to_package.extend(license_files)
    
    # 过滤掉不存在的文件
    files_to_package = [f for f in files_to_package if f and os.path.exists(f)]
    
    # 添加可能存在的其他必要文件
    for pattern in ['requirements.txt', '*.png', '*.jpg', '*.ico']:
        matching_files = glob.glob(pattern)
        for file in matching_files:
            if file not in files_to_package:
                files_to_package.append(file)
    
    # 创建ZIP文件
    zip_filename = f"{module_id}.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 添加普通文件
        for file in files_to_package:
            if os.path.exists(file):
                zipf.write(file)
                print(f"添加文件到压缩包: {file}")
        
        # 添加bin目录下的可执行文件
        bin_dir = "bin"
        if os.path.exists(bin_dir):
            for root, dirs, files in os.walk(bin_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path)
                    print(f"添加可执行文件到压缩包: {file_path}")
        
        # 添加cli目录及其内容
        cli_dir = "cli"
        if os.path.exists(cli_dir):
            for root, dirs, files in os.walk(cli_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path)
                    print(f"添加CLI文件到压缩包: {file_path}")
    
    # 计算压缩包的哈希值
    zip_hash = calculate_file_hash(zip_filename)
    zip_size = os.path.getsize(zip_filename) / 1024  # 转换为KB
    
    # 更新 update.json
    repo_owner_name = os.environ.get('GITHUB_REPOSITORY', '').split('/')
    if len(repo_owner_name) == 2:
        repo_owner, repo_name = repo_owner_name
    else:
        repo_owner = 'light'
        repo_name = module_id
    
    update_json = {
        "version": args.version,
        "versionCode": version_code,
        "zipUrl": f"https://github.com/{repo_owner}/{repo_name}/releases/download/v{args.version}/{module_id}.zip",
        "changelog": f"https://github.com/{repo_owner}/{repo_name}/blob/main/CHANGELOG.MD",
        "sha256": zip_hash,
        "size": round(zip_size, 2)
    }
    
    with open('update.json', 'w', encoding='utf-8') as f:
        # 使用 indent=4 以保持格式一致
        json.dump(update_json, f, ensure_ascii=False, indent=4)
    
    # 获取更新日志内容
    changelog_content = args.changelog
    if not changelog_content and os.path.exists('CHANGELOG.MD'):
        changelog_content = extract_latest_changelog('CHANGELOG.MD')
        if changelog_content:
            print(f"使用 CHANGELOG.MD 中的最新更新日志")
        else:
            changelog_content = f"版本 {args.version} 发布"
    
    # 创建包含哈希值的发布说明
    release_notes = (
        f"## {module_id} v{args.version} (版本代号: {version_code})\n\n"
        f"{changelog_content or f'版本 {args.version} 发布'}\n\n"
        f"### 下载信息\n\n"
        f"- 文件: [{module_id}.zip]({update_json['zipUrl']})\n"
        f"- 大小: {round(zip_size, 2)} KB\n"
        f"- SHA256: `{zip_hash}`\n\n"
        f"### 构建信息\n\n"
        f"- 构建时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"- Python版本: {open('.python-version').read().strip() if os.path.exists('.python-version') else '未指定'}\n"
    )
    
    # 将发布说明保存到文件
    release_notes_file = 'RELEASE_NOTES.md'
    with open(release_notes_file, 'w', encoding='utf-8') as f:
        f.write(release_notes)
    
    # 更新 CHANGELOG.MD
    if os.path.exists('CHANGELOG.MD') and args.changelog:
        # 如果提供了更新日志并且已存在 CHANGELOG.MD，则更新它
        try:
            with open('CHANGELOG.MD', 'r', encoding='utf-8') as f:
                content = f.read()
            
            today = datetime.datetime.now().strftime('%Y-%m-%d')
            new_entry = f"## [{args.version}] - {today}\n\n{args.changelog}\n\n"
            
            # 查找第一个版本条目位置，并在其前插入新条目
            first_version_entry = re.search(r'## \[.*?\]', content)
            if first_version_entry:
                position = first_version_entry.start()
                updated_content = content[:position] + new_entry + content[position:]
            else:
                # 如果找不到任何版本条目，则添加到文件末尾
                updated_content = content.rstrip() + "\n\n" + new_entry
            
            with open('CHANGELOG.MD', 'w', encoding='utf-8') as f:
                f.write(updated_content)
        except Exception as e:
            print(f"更新 CHANGELOG.MD 时出错: {e}")
    
    # 设置输出变量供 GitHub Actions 使用
    os.environ['MODULE_ID'] = module_id
    os.environ['VERSION'] = args.version
    os.environ['VERSION_CODE'] = str(version_code)
    os.environ['CHANGELOG'] = changelog_content or f"版本 {args.version} 发布"
    os.environ['SHA256'] = zip_hash
    os.environ['FILE_SIZE'] = str(round(zip_size, 2))
    os.environ['RELEASE_NOTES'] = release_notes
    
    print(f"::set-output name=module_id::{module_id}")
    print(f"::set-output name=version::{args.version}")
    print(f"::set-output name=version_code::{version_code}")
    print(f"::set-output name=changelog::{changelog_content or f'版本 {args.version} 发布'}")
    print(f"::set-output name=sha256::{zip_hash}")
    print(f"::set-output name=file_size::{round(zip_size, 2)}")
    print(f"::set-output name=release_notes_file::{release_notes_file}")
    
    print(f"\n打包内容摘要:")
    print(f"模块ID: {module_id}")
    print(f"版本: {args.version}")
    print(f"版本代号: {version_code}")
    print(f"许可证类型: {meta_data.get('license', '未指定')}")
    print(f"包含CLI目录: {'是' if os.path.exists('cli') else '否'}")
    print(f"包含bin目录: {'是' if os.path.exists('bin') else '否'}")
    print(f"Python版本: {open('.python-version').read().strip() if os.path.exists('.python-version') else '未指定'}")
    print(f"压缩包大小: {round(zip_size, 2)} KB")
    print(f"SHA256: {zip_hash}")
    print(f"\n模块已打包为: {zip_filename}")
    print(f"发布说明已保存至: {release_notes_file}")
    
    # 清理临时文件和目录
    temp_dirs = ["build", "__pycache__", ".pytest_cache"]
    for dir_name in temp_dirs:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"已清理临时目录: {dir_name}")
            except Exception as e:
                print(f"清理 {dir_name} 时出错: {e}")

if __name__ == "__main__":
    main()