# -*- coding: utf-8 -*-
"""
素材库管理器 — 上传/列出/分类管理项目素材（图纸/图片/文档/表格）
"""
import json
import sys
import shutil
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(r"D:\fanben\施工方案生成系统")
PROJECT_DIR = BASE_DIR / "项目"
INDEX_FILE = PROJECT_DIR / "项目索引.json"

# 文件类型 → 分类映射
FILE_CATEGORY_MAP = {
    # 图纸
    ".dwg": "图纸", ".dxf": "图纸", ".dwt": "图纸",
    # 图片
    ".jpg": "图片", ".jpeg": "图片", ".png": "图片",
    ".gif": "图片", ".bmp": "图片", ".tiff": "图片",
    ".tif": "图片", ".webp": "图片", ".svg": "图片",
    # 文档
    ".pdf": "文档", ".doc": "文档", ".docx": "文档",
    ".txt": "文档", ".md": "文档", ".rtf": "文档",
    # 表格
    ".xls": "表格", ".xlsx": "表格", ".csv": "表格",
    ".xlsm": "表格", ".xlsb": "表格",
}

CATEGORY_ICONS = {
    "图纸": "📐", "图片": "🖼️", "文档": "📝", "表格": "📊", "其他": "📦"
}

def load_index():
    if INDEX_FILE.exists():
        with open(INDEX_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {"projects": []}

def classify_file(filepath):
    """根据扩展名自动分类"""
    ext = Path(filepath).suffix.lower()
    return FILE_CATEGORY_MAP.get(ext, "其他")

def get_category_dir(proj_dir, category):
    """获取分类目录，确保存在"""
    cat_dir = proj_dir / "素材库" / category
    cat_dir.mkdir(parents=True, exist_ok=True)
    return cat_dir

def list_materials(proj_id, category=None):
    """列出项目素材"""
    data = load_index()
    p = next((p for p in data["projects"] if p["id"] == proj_id), None)
    if not p:
        print(f"❌ 未找到项目: {proj_id}")
        return
    
    proj_dir = PROJECT_DIR / p.get("dir_name", proj_id)
    mat_dir = proj_dir / "素材库"
    
    if not mat_dir.exists():
        print(f"\n📭 素材库为空")
        print(f"   目录: {mat_dir}")
        print(f"   上传素材: python 技能/manage_materials.py upload {proj_id} <文件路径>")
        return
    
    categories = [category] if category else ["图纸", "图片", "文档", "表格", "其他"]
    
    total_files = 0
    total_size = 0
    
    print(f"\n{'='*60}")
    print(f"  📦 素材库 — {p['name']}")
    print(f"{'='*60}")
    
    for cat in categories:
        cat_dir = mat_dir / cat
        if not cat_dir.exists():
            continue
        
        files = list(cat_dir.iterdir())
        if not files:
            continue
        
        cat_size = 0
        print(f"\n  {CATEGORY_ICONS.get(cat, '📦')} {cat}（{len(files)} 个文件）")
        print(f"  {'-'*50}")
        
        for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
            if f.is_file():
                size_kb = f.stat().st_size / 1024
                mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
                print(f"    {f.name}")
                print(f"       大小: {size_str} | 修改: {mtime}")
                cat_size += f.stat().st_size
                total_files += 1
        
        total_size += cat_size
    
    if total_files == 0:
        print(f"\n  📭 素材库为空")
    else:
        total_str = f"{total_size/1024:.0f} KB" if total_size < 1024*1024 else f"{total_size/1024/1024:.1f} MB"
        print(f"\n  {'='*50}")
        print(f"  📊 合计: {total_files} 个文件，{total_str}")
    
    print(f"\n{'='*60}")
    print(f"  上传:     python 技能/manage_materials.py upload {proj_id} <文件路径>")
    print(f"  筛选分类: python 技能/manage_materials.py list {proj_id} 图纸")
    print(f"{'='*60}\n")

def upload_material(proj_id, file_path, category=None):
    """上传文件到素材库"""
    data = load_index()
    p = next((p for p in data["projects"] if p["id"] == proj_id), None)
    if not p:
        print(f"❌ 未找到项目: {proj_id}")
        return
    
    src = Path(file_path)
    if not src.exists():
        print(f"❌ 文件不存在: {file_path}")
        return
    
    if src.is_dir():
        print(f"❌ 不支持目录，请逐个上传文件")
        return
    
    # 自动分类或使用指定分类
    if not category:
        category = classify_file(file_path)
    
    proj_dir = PROJECT_DIR / p.get("dir_name", proj_id)
    dest_dir = get_category_dir(proj_dir, category)
    dest = dest_dir / src.name
    
    # 处理重名
    if dest.exists():
        stem, ext = src.stem, src.suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = dest_dir / f"{stem}_{timestamp}{ext}"
    
    shutil.copy2(src, dest)
    size_kb = dest.stat().st_size / 1024
    size_str = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
    
    print(f"\n✅ 素材已上传！")
    print(f"   项目: {p['name']}")
    print(f"   分类: {CATEGORY_ICONS.get(category, '📦')} {category}")
    print(f"   文件: {dest.name}")
    print(f"   大小: {size_str}")
    print(f"   路径: {dest}")

def upload_batch(proj_id, pattern, category=None):
    """批量上传（支持通配符）"""
    from glob import glob
    files = glob(pattern)
    if not files:
        print(f"❌ 未匹配到文件: {pattern}")
        return
    
    print(f"\n📤 批量上传 {len(files)} 个文件到项目 {proj_id}...")
    success = 0
    for f in files:
        if Path(f).is_file():
            try:
                upload_material(proj_id, f, category)
                success += 1
            except Exception as e:
                print(f"  ❌ {f}: {e}")
    
    print(f"\n✅ 成功上传 {success}/{len(files)} 个文件")

def material_stats(proj_id):
    """素材统计"""
    data = load_index()
    p = next((p for p in data["projects"] if p["id"] == proj_id), None)
    if not p:
        print(f"❌ 未找到项目: {proj_id}")
        return
    
    proj_dir = PROJECT_DIR / p.get("dir_name", proj_id)
    mat_dir = proj_dir / "素材库"
    
    if not mat_dir.exists():
        print("素材库为空")
        return
    
    print(f"\n  📊 素材统计 — {p['name']}")
    print(f"  {'='*40}")
    
    total = 0
    for cat in ["图纸", "图片", "文档", "表格", "其他"]:
        cat_dir = mat_dir / cat
        count = len(list(cat_dir.glob("*"))) if cat_dir.exists() else 0
        size = sum(f.stat().st_size for f in cat_dir.glob("*") if f.is_file()) if cat_dir.exists() else 0
        size_str = f"{size/1024:.0f}KB" if size < 1024*1024 else f"{size/1024/1024:.1f}MB"
        print(f"  {CATEGORY_ICONS.get(cat, '📦')} {cat}: {count} 个文件 ({size_str})")
        total += count
    
    print(f"  {'='*40}")
    print(f"  总计: {total} 个文件")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("素材库管理器 — 用法:")
        print("  列出素材:   python 技能/manage_materials.py list <项目ID> [分类]")
        print("  上传素材:   python 技能/manage_materials.py upload <项目ID> <文件路径> [分类]")
        print("  批量上传:   python 技能/manage_materials.py batch <项目ID> <通配符> [分类]")
        print("  素材统计:   python 技能/manage_materials.py stats <项目ID>")
        print()
        print("  分类: 图纸 / 图片 / 文档 / 表格 / 其他")
        print("  示例:")
        print("    python 技能/manage_materials.py upload binjiang D:\\图纸\\结构图.dwg")
        print("    python 技能/manage_materials.py upload binjiang C:\\照片\\现场.jpg 图片")
        print("    python 技能/manage_materials.py batch  binjiang \"D:\\资料\\*.pdf\"")
    elif sys.argv[1] == "list":
        proj_id = sys.argv[2] if len(sys.argv) >= 3 else "binjiang"
        cat = sys.argv[3] if len(sys.argv) >= 4 else None
        list_materials(proj_id, cat)
    elif sys.argv[1] == "upload":
        if len(sys.argv) >= 4:
            cat = sys.argv[4] if len(sys.argv) >= 5 else None
            upload_material(sys.argv[2], sys.argv[3], cat)
        else:
            print("用法: python 技能/manage_materials.py upload <项目ID> <文件路径> [分类]")
    elif sys.argv[1] == "batch":
        if len(sys.argv) >= 4:
            cat = sys.argv[4] if len(sys.argv) >= 5 else None
            upload_batch(sys.argv[2], sys.argv[3], cat)
        else:
            print("用法: python 技能/manage_materials.py batch <项目ID> <通配符> [分类]")
    elif sys.argv[1] == "stats":
        proj_id = sys.argv[2] if len(sys.argv) >= 3 else "binjiang"
        material_stats(proj_id)
    else:
        print(f"未知命令: {sys.argv[1]}")
