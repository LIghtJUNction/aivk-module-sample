#!/usr/bin/env python3
import os
import toml
import argparse
import datetime
import zipfile
import glob

def main():
    parser = argparse.ArgumentParser(description='Package AIVK module')
    parser.add_argument('--version', required=True, help='New version number')
    parser.add_argument('--changelog', required=True, help='Changelog for this version')
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
    
    # 准备打包文件列表
    files_to_package = [
        'meta.toml',
        'config.toml' if os.path.exists('config.toml') else None,
        f"{module_id}.py" if os.path.exists(f"{module_id}.py") else None,
        'pyproject.toml' if os.path.exists('pyproject.toml') else None,
        'README.md' if os.path.exists('README.md') else None,
        'LICENSE' if os.path.exists('LICENSE') else None
    ]
    
    # 过滤掉不存在的文件
    files_to_package = [f for f in files_to_package if f]
    
    # 添加可能存在的其他必要文件
    for pattern in ['requirements.txt', '*.png', '*.jpg', '*.ico']:
        files_to_package.extend(glob.glob(pattern))
    
    # 创建ZIP文件
    zip_filename = f"{module_id}.zip"
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files_to_package:
            if os.path.exists(file):
                zipf.write(file)
    
    # 更新 update.json
    update_json = {
        "version": args.version,
        "versionCode": version_code,
        "url": f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}/releases/download/v{args.version}/{module_id}.zip",
        "changelog": args.changelog
    }
    
    with open('update.json', 'w', encoding='utf-8') as f:
        import json
        json.dump(update_json, f, ensure_ascii=False, indent=2)
    
    print(f"模块已打包为: {zip_filename}")
    print(f"版本: {args.version}")
    print(f"版本代号: {version_code}")

if __name__ == "__main__":
    main()