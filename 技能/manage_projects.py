# -*- coding: utf-8 -*-
"""
项目管理器 — 按项目整理方案：新建/列出/查看/添加方案
"""
import json
import sys
import shutil
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"D:\fanben\施工方案生成系统")
PROJECT_DIR = BASE_DIR / "项目"
INDEX_FILE = PROJECT_DIR / "项目索引.json"
OUTPUT_LEGACY = BASE_DIR / "输出"  # 旧输出目录

def load_index():
    if INDEX_FILE.exists():
        with open(INDEX_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {"projects": []}

def save_index(data):
    PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ===== 列出所有项目 =====

def list_projects():
    data = load_index()
    projs = data["projects"]
    print(f"\n{'='*60}")
    print(f"  📁 项目管理（共 {len(projs)} 个项目）")
    print(f"{'='*60}")
    
    if not projs:
        print(f"\n  暂无项目。使用以下命令创建：")
        print(f"    python 技能/manage_projects.py new <项目名称>")
        return
    
    for p in projs:
        scheme_count = len(p.get("schemes", []))
        status_tag = {"在建": "🔵", "竣工": "✅", "停工": "🔴", "规划": "📋"}.get(p["status"], "")
        print(f"\n  {status_tag} [{p['id']}] {p['name']}")
        print(f"     类型: {p['type']} | 状态: {p['status']} | 方案数: {scheme_count}")
        if p.get("summary"):
            summary = p["summary"]
            print(f"     规模: {summary.get('建筑面积', '?')} | {summary.get('结构', '?')}")
        if scheme_count > 0:
            for s in p["schemes"]:
                print(f"     📄 {s['name']} ({s['type']}) — {s['created']}")
    
    print(f"\n{'='*60}")
    print(f"  查看详情: python 技能/manage_projects.py show <项目ID>")
    print(f"  新建项目: python 技能/manage_projects.py new <项目名称>")
    print(f"{'='*60}\n")

# ===== 查看项目详情 =====

def show_project(proj_id):
    data = load_index()
    p = next((p for p in data["projects"] if p["id"] == proj_id), None)
    
    if not p:
        print(f"❌ 未找到项目: {proj_id}")
        ids = [p["id"] for p in data["projects"]]
        print(f"   可用ID: {', '.join(ids) if ids else '无'}")
        return
    
    print(f"\n{'='*60}")
    print(f"  📁 {p['name']}")
    print(f"{'='*60}")
    print(f"  ID:       {p['id']}")
    print(f"  类型:     {p['type']}")
    print(f"  状态:     {p['status']}")
    print(f"  创建:     {p['created']}")
    
    if p.get("summary"):
        print(f"\n  📊 工程概况:")
        for k, v in p["summary"].items():
            print(f"     {k}: {v}")
    
    schemes = p.get("schemes", [])
    print(f"\n  📄 方案清单（共 {len(schemes)} 份）:")
    if schemes:
        for i, s in enumerate(schemes, 1):
            print(f"     {i}. {s['name']}")
            print(f"        类型: {s['type']} | 日期: {s['created']}")
            print(f"        文件: {s.get('file', '无')}")
    else:
        print(f"     （暂无方案）")
    
    proj_path = PROJECT_DIR / p.get("dir_name", p["id"])
    if proj_path.exists():
        docx_files = list(proj_path.glob("方案/*.docx"))
        if docx_files:
            print(f"\n  📂 实际文件:")
            for f in docx_files:
                size_kb = f.stat().st_size / 1024
                print(f"     {f.name} ({size_kb:.0f} KB)")
    
    print(f"\n{'='*60}")
    print(f"  添加方案: python 技能/manage_projects.py add-scheme {proj_id} <方案名称> <方案类型>")
    print(f"{'='*60}\n")

# ===== 新建项目 =====

def new_project(name, proj_type="", status="在建"):
    # 生成 ID（拼音首字母简化 + 时间戳）
    import re
    short = re.sub(r'[^\u4e00-\u9fff]', '', name)[:4]
    proj_id = short if short else name[:8]
    
    data = load_index()
    
    # 检查重复
    if any(p["id"] == proj_id for p in data["projects"]):
        proj_id = f"{proj_id}_{datetime.now().strftime('%m%d')}"
    
    dir_name = name[:20].replace("/", "-").replace("\\", "-")
    
    project = {
        "id": proj_id,
        "name": name,
        "short_name": short,
        "type": proj_type,
        "status": status,
        "created": datetime.now().strftime("%Y-%m-%d"),
        "dir_name": dir_name,
        "summary": {},
        "schemes": []
    }
    
    data["projects"].append(project)
    save_index(data)
    
    # 创建项目目录
    proj_dir = PROJECT_DIR / dir_name
    (proj_dir / "方案").mkdir(parents=True, exist_ok=True)
    
    print(f"\n✅ 项目已创建！")
    print(f"   ID:   {proj_id}")
    print(f"   名称: {name}")
    print(f"   目录: {proj_dir}")
    print(f"\n   👉 下一步：python 技能/manage_projects.py show {proj_id}")
    
    return proj_id, project

# ===== 添加方案记录 =====

def add_scheme(proj_id, scheme_name, scheme_type, file_path=""):
    data = load_index()
    p = next((p for p in data["projects"] if p["id"] == proj_id), None)
    
    if not p:
        print(f"❌ 未找到项目: {proj_id}")
        return
    
    scheme = {
        "name": scheme_name,
        "type": scheme_type,
        "created": datetime.now().strftime("%Y-%m-%d"),
        "file": file_path
    }
    
    if "schemes" not in p:
        p["schemes"] = []
    p["schemes"].append(scheme)
    save_index(data)
    
    print(f"✅ 已添加方案: {scheme_name} → {p['name']}")
    
    # 如果有文件，复制到项目方案目录
    if file_path and Path(file_path).exists():
        proj_dir = PROJECT_DIR / p.get("dir_name", proj_id)
        dest = proj_dir / "方案" / Path(file_path).name
        if str(Path(file_path).resolve()) != str(dest.resolve()):
            shutil.copy2(file_path, dest)
            print(f"   📄 已复制到: {dest}")

# ===== 迁移旧方案 =====

def migrate_legacy():
    """把旧输出目录的方案迁移到项目管理"""
    if not OUTPUT_LEGACY.exists():
        return
    
    docx_files = list(OUTPUT_LEGACY.glob("*.docx"))
    if not docx_files:
        return
    
    data = load_index()
    
    # 查找或创建"滨江花园"项目
    proj = next((p for p in data["projects"] if "滨江花园" in p.get("name", "")), None)
    
    if not proj:
        # 从配置加载参数
        config_path = BASE_DIR / "配置" / "项目参数.json"
        summary = {}
        if config_path.exists():
            with open(config_path, encoding='utf-8') as f:
                cfg = json.load(f)
            summary = {
                "建筑面积": f"{cfg.get('建设规模', {}).get('总建筑面积_平米', '?')}㎡",
                "结构": cfg.get('结构类型', '?'),
                "工期": f"{cfg.get('合同工期', {}).get('总工期_天', '?')}天"
            }
        
        proj_id, proj = new_project(
            "XX市滨江花园住宅小区项目",
            proj_type="住宅",
            status="在建"
        )
        if summary:
            proj["summary"] = summary
            save_index(data)
    
    # 复制方案文件
    proj_dir = PROJECT_DIR / proj.get("dir_name", proj["id"])
    (proj_dir / "方案").mkdir(parents=True, exist_ok=True)
    for f in docx_files:
        dest = proj_dir / "方案" / f.name
        if not dest.exists():
            shutil.copy2(f, dest)
            print(f"📦 迁移: {f.name} → {dest}")
        
        # 添加方案记录
        if not any(s.get("file") == f"方案/{f.name}" for s in proj.get("schemes", [])):
            add_scheme(proj["id"], f.stem, "总体", f"方案/{f.name}")
    
    print(f"✅ 迁移完成")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        list_projects()
    elif sys.argv[1] == "show" and len(sys.argv) >= 3:
        show_project(sys.argv[2])
    elif sys.argv[1] == "new" and len(sys.argv) >= 3:
        name = sys.argv[2]
        ptype = sys.argv[3] if len(sys.argv) >= 4 else ""
        status = sys.argv[4] if len(sys.argv) >= 5 else "在建"
        new_project(name, ptype, status)
    elif sys.argv[1] == "add-scheme" and len(sys.argv) >= 5:
        add_scheme(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) >= 6 else "")
    elif sys.argv[1] == "migrate":
        migrate_legacy()
    else:
        print(f"用法:")
        print(f"  列出项目:     python 技能/manage_projects.py")
        print(f"  查看详情:     python 技能/manage_projects.py show <项目ID>")
        print(f"  新建项目:     python 技能/manage_projects.py new <名称> [类型] [状态]")
        print(f"  添加方案:     python 技能/manage_projects.py add-scheme <项目ID> <方案名> <类型> [文件路径]")
        print(f"  迁移旧方案:   python 技能/manage_projects.py migrate")
