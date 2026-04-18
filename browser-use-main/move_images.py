#import os
import shutil
from pathlib import Path
from datetime import datetime

def move_and_clear_images():
    """
    清空 image 文件夹，并将内容移动到 history 文件夹
    同时清空 Information.md 文件
    """
    # 定义路径
    base_dir = Path(r"D:\desktop\browser-use-main")
    image_dir = base_dir / "image"
    history_dir = base_dir / "history"
    information_file = base_dir / "Information.md"
    
    # 创建 history 文件夹（如果不存在）
    history_dir.mkdir(exist_ok=True)

    # 生成带时间戳的子文件夹名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir = history_dir / f"image_backup_{timestamp}"
    target_dir.mkdir(exist_ok=True)
    
    # === 第一部分：处理 image 文件夹 ===
    # 检查 image 文件夹是否存在
    if image_dir.exists():
        # 获取 image 文件夹中的所有文件
        files = list(image_dir.glob("*"))
        
        if files:
            print(f"[信息] 准备移动 {len(files)} 个图片文件...")
            
            # 移动文件
            moved_count = 0
            for file_path in files:
                try:
                    if file_path.is_file():
                        shutil.move(str(file_path), str(target_dir / file_path.name))
                        moved_count += 1
                        print(f"  [成功] {file_path.name}")
                    elif file_path.is_dir():
                        shutil.move(str(file_path), str(target_dir / file_path.name))
                        moved_count += 1
                        print(f"  [成功] [目录] {file_path.name}")
                except Exception as e:
                    print(f"  [失败] 移动失败 {file_path.name}: {e}")
            
            print(f"\n[成功] 完成！成功移动 {moved_count}/{len(files)} 个图片文件")
            print(f"[信息] 目标位置：{target_dir}")
        else:
            print(f"[警告] image 文件夹为空")
    else:
        print(f"[警告] image 文件夹不存在：{image_dir}")
    
    # === 第二部分：清空 Information.md 文件 ===
    if information_file.exists():
        try:
            # 显示确认提示
            print(f"\n{'=' * 60}")
            print("⚠️  即将清空 Information.md 文件")
            print(f"{'=' * 60}")
            print(f"  文件路径: {information_file}")
            
            # 显示当前文件内容预览（前200字符）
            with open(information_file, 'r', encoding='utf-8') as f:
                preview = f.read()[:200]
                if preview:
                    print(f"  当前内容预览:")
                    for line in preview.split('\n')[:10]:
                        print(f"    {line}")
                    if len(preview.split('\n')) > 10:
                        print("    ...")
                else:
                    print("  当前文件为空")
            
            print(f"{'=' * 60}")
            
            # 手动确认
            while True:
                confirm = input("\n❓ 是否确认清空 Information.md 文件? (y/n): ").strip().lower()
                if confirm in ['y', 'yes', '是']:
                    # 用户确认，继续执行
                    break
                elif confirm in ['n', 'no', '否']:
                    print("[取消] 已取消清空操作，保留 Information.md 文件")
                    return True  # 返回 True 表示图片移动成功，只是跳过了清空操作
                else:
                    print("  ⚠️  请输入 y (确认) 或 n (取消)")
            
            # 备份当前 Information.md 到 history 目录
            backup_info_file = target_dir / "Information.md"
            shutil.copy2(str(information_file), str(backup_info_file))
            print(f"\n[信息] 已备份 Information.md 到: {backup_info_file}")
            
            # 清空文件内容
            with open(information_file, 'w', encoding='utf-8') as f:
                f.write('')
            print(f"[成功] Information.md 已清空")
        except Exception as e:
            print(f"[失败] 清空 Information.md 失败: {e}")
    else:
        print(f"[警告] Information.md 文件不存在，跳过清空操作")
    
    return True

if __name__ == "__main__":
    try:
        move_and_clear_images()
    except Exception as e:
        print(f"[错误] 程序执行失败：{e}")
