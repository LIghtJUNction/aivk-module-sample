#!/usr/bin/env python3
import os
import toml
import argparse
import datetime
import shutil
import glob

def main():
    parser = argparse.ArgumentParser(description='Initialize AIVK module')
    parser.add_argument('--new_id', required=True, help='New module ID')
    parser.add_argument('--description', required=True, help='Module description')
    parser.add_argument('--author', required=True, help='Module author')
    args = parser.parse_args()
    
    # 读取 meta.toml
    meta_path = 'meta.toml'
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta_data = toml.load(f)
    
    # 获取当前模块 ID
    current_id = meta_data.get('id', 'sampleModuleID')
    
    # 更新 meta.toml
    meta_data['id'] = args.new_id
    meta_data['name'] = args.new_id  # 可以根据需要修改
    meta_data['description'] = args.description
    meta_data['author'] = args.author
    meta_data['version'] = '0.0.0'
    
    # 生成版本代号 (年月日序列)
    now = datetime.datetime.now()
    version_code = int(f"{now.year % 100}{now.month:02d}{now.day:02d}01")
    meta_data['versionCode'] = version_code
    
    # 更新 updateJson
    repo_url = os.environ.get('GITHUB_REPOSITORY', '')
    if repo_url:
        meta_data['updateJson'] = f"https://raw.githubusercontent.com/{repo_url}/main/update.json"
    
    # 检测仓库 LICENSE
    license_file = glob.glob('LICENSE*')
    if license_file:
        with open(license_file[0], 'r', encoding='utf-8') as f:
            first_line = f.readline().strip().upper()
            if 'MIT' in first_line:
                meta_data['license'] = 'MIT'
            elif 'APACHE' in first_line:
                meta_data['license'] = 'Apache-2.0'
            elif 'GPL' in first_line:
                meta_data['license'] = 'GPL-3.0'
            # 其他许可证类型...
    
    # 写回 meta.toml
    with open(meta_path, 'w', encoding='utf-8') as f:
        toml.dump(meta_data, f)
    
    # 重命名模块文件
    py_file = f"{current_id}.py"
    if os.path.exists(py_file):
        shutil.move(py_file, f"{args.new_id}.py")
    else:
        # 查找任何可能的模块文件并重命名
        module_files = glob.glob("moduleID.py")
        if module_files:
            shutil.move(module_files[0], f"{args.new_id}.py")
        else:
            py_files = glob.glob("*.py")
            for py_file in py_files:
                if py_file != "__init__.py" and not py_file.startswith("test_"):
                    shutil.move(py_file, f"{args.new_id}.py")
                    break
    
    # 创建初始的 update.json
    update_json = {
        "version": "0.0.0",
        "versionCode": version_code,
        "url": f"https://github.com/{os.environ.get('GITHUB_REPOSITORY', '')}/releases/download/v0.0.0/{args.new_id}.zip",
        "changelog": f"初始化模块: {args.new_id}"
    }
    
    with open('update.json', 'w', encoding='utf-8') as f:
        import json
        json.dump(update_json, f, ensure_ascii=False, indent=2)
    
    # 更新modules列表
    if 'modules' in meta_data and isinstance(meta_data['modules'], list):
        if current_id in meta_data['modules']:
            meta_data['modules'].remove(current_id)
            meta_data['modules'].append(args.new_id)
        
        # 写回 meta.toml
        with open(meta_path, 'w', encoding='utf-8') as f:
            toml.dump(meta_data, f)

if __name__ == "__main__":
    main()