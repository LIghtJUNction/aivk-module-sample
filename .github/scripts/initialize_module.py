#!/usr/bin/env python3
import os
import toml
import argparse
import datetime
import shutil
import glob
import json

def main():
    parser = argparse.ArgumentParser(description='Initialize AIVK module')
    parser.add_argument('--new_id', required=True, help='New module ID')
    parser.add_argument('--description', required=True, help='Module description')
    parser.add_argument('--author', required=True, help='Module author')
    parser.add_argument('--name', help='Module name (defaults to new_id if not provided)')
    parser.add_argument('--type', choices=['module', 'modules'], default='module',
                       help='Module type: "module" for single module or "modules" for multiple modules package')
    args = parser.parse_args()
    
    # 读取 meta.toml
    meta_path = 'meta.toml'
    with open(meta_path, 'r', encoding='utf-8') as f:
        meta_data = toml.load(f)
    
    # 获取当前模块 ID
    current_id = meta_data.get('id', 'sampleModuleID')
    
    # 更新 meta.toml 基本信息
    meta_data['type'] = args.type
    meta_data['id'] = args.new_id
    meta_data['name'] = args.name if args.name else args.new_id
    meta_data['description'] = args.description
    meta_data['author'] = args.author
    meta_data['version'] = '0.0.0'
    
    # 生成版本代号 (年月日序列)
    now = datetime.datetime.now()
    version_code = int(f"{now.year % 100}{now.month:02d}{now.day:02d}01")
    meta_data['versionCode'] = version_code
    
    # 处理 modules 列表
    if args.type == 'modules':
        if 'modules' not in meta_data or not isinstance(meta_data['modules'], list):
            meta_data['modules'] = []
        if current_id in meta_data['modules']:
            meta_data['modules'].remove(current_id)
        meta_data['modules'].append(args.new_id)
    else:  # 单模块模式
        meta_data['modules'] = [args.new_id]
    
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
    
    # 默认设置启动模式
    if 'startMode' not in meta_data:
        meta_data['startMode'] = 'import'
    
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
    
    # 更新模块文件中的模块 ID 信息
    module_file = f"{args.new_id}.py"
    if os.path.exists(module_file):
        with open(module_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换模块文档字符串中的信息
        content = content.replace('Module ID : example_module', f'Module ID : {args.new_id}')
        content = content.replace('Module Name : Example Module', f'Module Name : {meta_data["name"]}')
        content = content.replace('Module Version : 0.1.0', 'Module Version : 0.0.0')
        content = content.replace('Module Author : LIghtJUNction', f'Module Author : {args.author}')
        content = content.replace('Module Description : Example module for AIVK', f'Module Description : {args.description}')
        
        with open(module_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    # 创建初始的 update.json
    repo_owner_name = os.environ.get('GITHUB_REPOSITORY', '').split('/')
    if len(repo_owner_name) == 2:
        repo_owner, repo_name = repo_owner_name
    else:
        repo_owner = 'owner'
        repo_name = args.new_id
    
    update_json = {
        "version": "0.0.0",
        "versionCode": version_code,
        "zipUrl": f"https://github.com/{repo_owner}/{repo_name}/releases/download/v0.0.0/{args.new_id}.zip",
        "changelog": f"https://github.com/{repo_owner}/{repo_name}/blob/main/CHANGELOG.MD"
    }
    
    with open('update.json', 'w', encoding='utf-8') as f:
        # 使用 indent=4 以保持格式一致
        json.dump(update_json, f, ensure_ascii=False, indent=4)
    
    # 更新 pyproject.toml
    if os.path.exists('pyproject.toml'):
        try:
            with open('pyproject.toml', 'r', encoding='utf-8') as f:
                pyproject_data = toml.load(f)
            
            if 'project' in pyproject_data:
                pyproject_data['project']['name'] = args.new_id
                pyproject_data['project']['version'] = '0.0.0'
                pyproject_data['project']['description'] = args.description
                
                if 'authors' in pyproject_data['project']:
                    for author_data in pyproject_data['project']['authors']:
                        if isinstance(author_data, dict) and 'name' in author_data:
                            author_data['name'] = args.author
                            break
            
            with open('pyproject.toml', 'w', encoding='utf-8') as f:
                toml.dump(pyproject_data, f)
                
        except Exception as e:
            print(f"更新 pyproject.toml 时出错: {e}")
    
    # 更新 CHANGELOG.MD
    if os.path.exists('CHANGELOG.MD'):
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        changelog_content = f"""# Changelog / 更新日志

## [0.0.0] - {today}

### 中文

#### 新增
- 初始版本
- {args.description}


### English

#### Added
- Initial release
- {args.description}
"""
        with open('CHANGELOG.MD', 'w', encoding='utf-8') as f:
            f.write(changelog_content)

if __name__ == "__main__":
    main()