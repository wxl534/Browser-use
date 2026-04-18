import requests
import json
import socket
import os
import re
import time
from openai import OpenAI

# 临时解决方案：绑定 hosts
# 10.64.84.182 openapi.seu.edu.cn
old_getaddrinfo = socket.getaddrinfo

def new_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if host == 'openapi.seu.edu.cn':
        host = '10.64.84.182'
    return old_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = new_getaddrinfo

# 模型配置
API_URL = "https://api.deepseek.com/v1/"
API_KEY = "sk-06237e1c2f1849e680d50bfbda613fd2"
MODEL_NAME = "deepseek-chat"

# 初始化 OpenAI 客户端
client = OpenAI(
    api_key=API_KEY,
    base_url=API_URL  # 注意: base_url 需要以 / 结尾
)

# ==================== 任务配置区域 ====================
# 配置文件路径
INPUT_FILE = r"D:\desktop\browser-use-main\source.html"
OUTPUT_FILE = r"D:\desktop\browser-use-main\Information.md"

# 只需在这里输入一句话描述任务（可使用 {input_file} 和 {output_file} 占位符）
TASK_DESCRIPTION = "读取 {input_file} 文件内容,分析源代码并提取介绍主图片信息的HTML代码段的首尾行,将他们写入到 {output_file}"

# 自动构建任务结构
TASKS = [
    {
        "name": "HTML分析任务",
        "description": TASK_DESCRIPTION.format(input_file=INPUT_FILE, output_file=OUTPUT_FILE),
    }
]

SELECTED_TASK_INDEX = 0
# ====================================================

def read_file_content(file_path):
    """读取文件内容"""
    print(f"  → 尝试读取: {file_path}")
    print(f"  → 文件存在: {os.path.exists(file_path)}")
    try:
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return f"错误：文件不存在 - {file_path}"
        
        # 检查文件大小（限制读取大文件）
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            return f"错误：文件过大 ({file_size / 1024 / 1024:.2f}MB)，无法读取"
        
        # 读取文件
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content
    except UnicodeDecodeError:
        # 如果UTF-8解码失败，尝试其他编码
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                content = f.read()
            return content
        except Exception as e:
            return f"错误：无法读取文件 - {str(e)}"
    except Exception as e:
        return f"错误：读取文件时发生异常 - {str(e)}"

def write_file_content(file_path, content):
    """写入文件内容"""
    try:
        # 确保目录存在
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ 创建目录: {directory}")
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True, f"✓ 文件写入成功: {file_path}"
    except Exception as e:
        return False, f"错误：写入文件失败 - {str(e)}"

def extract_file_path(text):
    """从文本中提取Windows文件路径"""
    # 先清理 markdown 反引号和多余字符
    text = text.replace('`', '').replace('\n', ' ').strip()
    
    # 匹配 Windows 完整路径（以常见文件扩展名结尾，路径中不含空格）
    path_pattern = r'([A-Za-z]:\\[\w\\.\-_]+?\.(?:html|htm|md|txt|json|xml|csv))'
    paths = re.findall(path_pattern, text, re.IGNORECASE)
    
    if paths:
        path = paths[0].strip().rstrip('"\' ')  
        return path
    
    # 备用：匹配包含目录的路径（不含空格）
    path_pattern2 = r'([A-Za-z]:\\(?:[\w\\.\-_]+\\)+[\w\\.\-_]+)'
    paths2 = re.findall(path_pattern2, text)
    
    if paths2:
        path = min(paths2, key=len).strip().rstrip('"\' `')
        return path
    
    return None

def extract_code_block_content(text):
    """从文本中提取代码块内容"""
    content_match = re.search(r'```(?:markdown)?\s*\n(.*?)\n```', text, re.DOTALL)
    return content_match.group(1) if content_match else None

def execute_task(task):
    """执行任务"""
    print(f"\n📋 任务: {task['description'][:80]}...")
    
    # 构建系统提示，严格限制文件操作
    system_prompt = f"""你是一个智能任务执行助手。

【重要规则】
1. 只能读取输入文件: {INPUT_FILE}
2. 只能写入输出文件: {OUTPUT_FILE}
3. 绝对禁止修改、写入或覆盖输入文件！
4. 分析结果必须写入输出文件

可用工具：
1. 读取文件：读取 {INPUT_FILE}
2. 写入文件：写入 {OUTPUT_FILE}
3. 分析处理：分析、总结、转换内容

执行规则：
- 先读取输入文件进行分析
- 分析完成后，将结果写入输出文件
- 写入文件时使用 ```markdown 代码块包裹内容
- 写入成功后报告任务完成"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"""请执行任务：{task['description']}

【操作步骤】
1. 读取文件: {INPUT_FILE}
2. 分析 HTML 内容，提取主图片信息相关代码段的首尾行标记
3. 将分析结果写入文件: {OUTPUT_FILE}（使用 ```markdown 代码块）
4. 报告"任务完成"

【重要提醒】
- 只能写入 {OUTPUT_FILE}
- 绝对不要修改 {INPUT_FILE}

请开始执行"""}
    ]
    
    # 执行任务的主循环
    max_iterations = 10  # 防止无限循环
    iteration = 0
    read_count = 0  # 记录读取次数
    write_count = 0  # 记录写入次数
    
    while iteration < max_iterations:
        iteration += 1
        print(f"\n[迭代 {iteration}/{max_iterations}] LLM思考中...", end="", flush=True)
        
        # 构造请求
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7
        }
        
        try:
            # 使用 OpenAI SDK 发送请求
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=4096,
                temperature=0.7
            )
            
            assistant_reply = response.choices[0].message.content
            print(" ✓")
            
            # 将 AI 回复添加到对话历史
            messages.append({"role": "assistant", "content": assistant_reply})
            
            # 检查是否需要读取文件
            file_path = extract_file_path(assistant_reply)
            if file_path and ('读取' in assistant_reply or 'read' in assistant_reply.lower()):
                # 防止重复读取
                if read_count >= 2:
                    print(f"  → 已读取过 {read_count} 次，跳过重复读取")
                    messages.append({
                        "role": "user",
                        "content": f"文件已经读取过了，请直接分析内容并写入 {OUTPUT_FILE}"
                    })
                    continue
                
                read_count += 1
                print(f"  → 读取文件: {os.path.basename(file_path)}")
                print(f"  → 完整路径: {file_path}")
                file_content = read_file_content(file_path)
                
                if not file_content.startswith("错误："):
                    print(f"  ✓ 读取成功，文件大小: {len(file_content)} 字符")
                    # 显示 LLM 回复摘要
                    print(f"  → LLM意图: {assistant_reply[:100]}...")
                    messages.append({
                        "role": "user",
                        "content": f"文件 {file_path} 的内容:\n{file_content[:5000]}"
                    })
                else:
                    print(f"  ✗ {file_content}")
                    messages.append({
                        "role": "user",
                        "content": f"读取文件失败:{file_content}"
                    })
                continue
                        
            # 检查是否需要写入文件
            if file_path and ('写入' in assistant_reply or 'write' in assistant_reply.lower() or '保存' in assistant_reply):
                # 【关键检查】验证写入路径是否为输出文件
                if os.path.abspath(file_path) != os.path.abspath(OUTPUT_FILE):
                    print(f"  ✗ 错误：LLM 尝试写入错误文件")
                    print(f"  → 期望写入: {OUTPUT_FILE}")
                    print(f"  → 实际路径: {file_path}")
                    print(f"  → 拒绝写入，保护输入文件")
                    messages.append({
                        "role": "user",
                        "content": f"错误！你尝试写入 {file_path}，但应该写入 {OUTPUT_FILE}。请重新生成内容并写入正确的输出文件。"
                    })
                    continue
                
                content_to_write = extract_code_block_content(assistant_reply)
                
                # 显示 LLM 回复摘要
                print(f"  → LLM意图: {assistant_reply[:100]}...")
                            
                if not content_to_write:
                    print(f"  ✗ 未找到代码块内容")
                    print(f"  → LLM回复预览: {assistant_reply[:200]}")
                    messages.append({
                        "role": "user",
                        "content": f"请明确指出要写入文件的具体内容，用 ```markdown 代码块包裹。\n\n你当前的回复：\n{assistant_reply[:500]}"
                    })
                    continue
                            
                write_count += 1
                print(f"  → 写入文件: {os.path.basename(file_path)}")
                print(f"  → 完整路径: {file_path}")
                print(f"  → 内容大小: {len(content_to_write)} 字符")
                success, message = write_file_content(file_path, content_to_write)
                if success:
                    print(f"  ✓ 写入成功")
                else:
                    print(f"  ✗ 写入失败: {message}")
                            
                messages.append({
                    "role": "user",
                    "content": f"文件写入{'成功' if success else '失败'}:{message}"
                })
                continue
            
            # 检查任务是否完成
            if '任务完成' in assistant_reply or 'task complete' in assistant_reply.lower() or '已完成' in assistant_reply:
                return True
            
            # 如果 AI 没有明确的操作指示，询问下一步
            messages.append({
                "role": "user",
                "content": "请继续执行下一步骤，或报告当前进度。如果需要操作文件，请明确指出文件路径和操作内容。"
            })
            
        except Exception as e:
            print(f" ✗")
            print(f"✗ 错误: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    print("⚠ 达到最大迭代次数")
    print(f"  统计: 读取 {read_count} 次, 写入 {write_count} 次")
    return False

# ==================== 主程序入口 ====================
if __name__ == "__main__":
    print("=" * 60)
    print("HTML 分析工具")
    print("=" * 60)
    print(f"\n输入文件: {INPUT_FILE}")
    print(f"输出文件: {OUTPUT_FILE}")
    print(f"任务描述: {TASK_DESCRIPTION[:80]}...")
    print("\n" + "-" * 60)
    
    # 直接执行选中的任务
    if SELECTED_TASK_INDEX < len(TASKS):
        start_time = None
        try:
            start_time = time.time()
            success = execute_task(TASKS[SELECTED_TASK_INDEX])
            elapsed = time.time() - start_time
            
            print("\n" + "=" * 60)
            if success:
                print("✓ HTML分析完成")
                print(f"  耗时: {elapsed:.2f} 秒")
                print(f"  输出文件: {OUTPUT_FILE}")
                
                # 检查输出文件是否存在
                if os.path.exists(OUTPUT_FILE):
                    file_size = os.path.getsize(OUTPUT_FILE)
                    print(f"  文件大小: {file_size:,} 字节")
                else:
                    print("  ⚠ 警告：输出文件未生成")
            else:
                print("✗ HTML分析失败")
                print(f"  耗时: {elapsed:.2f} 秒")
                print("  请检查上方错误信息")
            print("=" * 60)
        except KeyboardInterrupt:
            print("\n\n⚠ 用户中断执行")
            if start_time:
                elapsed = time.time() - start_time
                print(f"  已运行: {elapsed:.2f} 秒")
        except Exception as e:
            print(f"\n✗ 发生异常: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print(f"错误:任务索引 {SELECTED_TASK_INDEX} 超出范围")

