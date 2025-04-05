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
    
    # 准备打包文件列表
    files_to_package = [
        'meta.toml',
        'config.toml' if os.path.exists('config.toml') else None,
        f"{module_id}.py" if os.path.exists(f"{module_id}.py") else None,
        'pyproject.toml' if os.path.exists('pyproject.toml') else None,
        'README.md' if os.path.exists('README.md') else None,
        'LICENSE' if os.path.exists('LICENSE') else None,
        'CHANGELOG.MD' if os.path.exists('CHANGELOG.MD') else None
    ]
    
    # 过滤掉不存在的文件
    files_to_package = [f for f in files_to_package if f]
    
    # 添加可能存在的其他必要文件
    for pattern in ['requirements.txt', '*.png', '*.jpg', '*.ico']:
        files_to_package.extend(glob.glob(pattern))
    
    # 创建ZIP文件
    zip_filename = f"{module_id}.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 添加普通文件
        for file in files_to_package:
            if os.path.exists(file):
                zipf.write(file)
        
        # 添加bin目录下的可执行文件
        bin_dir = "bin"
        if os.path.exists(bin_dir):
            for root, _, files in os.walk(bin_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path)
    
    # 更新 update.json
    repo_owner_name = os.environ.get('GITHUB_REPOSITORY', '').split('/')
    if len(repo_owner_name) == 2:
        repo_owner, repo_name = repo_owner_name
    else:
        repo_owner = 'owner'
        repo_name = module_id
    
    update_json = {
        "version": args.version,
        "versionCode": version_code,
        "zipUrl": f"https://github.com/{repo_owner}/{repo_name}/releases/download/v{args.version}/{module_id}.zip",
        "changelog": f"https://github.com/{repo_owner}/{repo_name}/blob/main/CHANGELOG.MD"
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
    
    print(f"::set-output name=module_id::{module_id}")
    print(f"::set-output name=version::{args.version}")
    print(f"::set-output name=version_code::{version_code}")
    print(f"::set-output name=changelog::{changelog_content or f'版本 {args.version} 发布'}")
    
    print(f"模块已打包为: {zip_filename}")
    print(f"版本: {args.version}")
    print(f"版本代号: {version_code}")
    
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