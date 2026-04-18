from browser_use import Agent, Browser, ChatBrowserUse, ActionResult
# from browser_use import ChatGoogle  # ChatGoogle(model='gemini-3-flash-preview')
# from browser_use import ChatAnthropic  # ChatAnthropic(model='claude-sonnet-4-6')
from browser_use import ChatOpenAI
from browser_use import Tools, Agent
from browser_use.agent.service import Agent, Tools
from browser_use.browser import BrowserSession
import asyncio
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import socket
import sys
import threading
import time

# 全局标志：用于控制是否退出
should_quit = False

def monitor_input_windows():
    """
    Windows 平台的后台线程：监听键盘输入，如果输入 'quit' 则设置退出标志
    """
    global should_quit
    import msvcrt
    
    print("\n💡 提示：在运行过程中输入 'quit' 可以停止程序运行")
    print("=" * 60 + "\n")
    
    input_buffer = []
    
    try:
        while not should_quit:
            # 非阻塞检查键盘输入
            if msvcrt.kbhit():
                char = msvcrt.getwch()
                
                # 处理回车键
                if char == '\r' or char == '\n':
                    command = ''.join(input_buffer).strip().lower()
                    input_buffer = []
                    
                    if command == 'quit':
                        print("\n\n⚠️  收到退出指令，正在停止运行...")
                        should_quit = True
                        break
                    elif command:  # 忽略空输入
                        print(f"\n⚠️  未知命令: {command}，请输入 'quit' 停止运行")
                elif char == '\b' or char == '\x08':  # 退格键
                    if input_buffer:
                        input_buffer.pop()
                        print('\b \b', end='', flush=True)  # 删除屏幕上的字符
                elif char == '\x03':  # Ctrl+C
                    should_quit = True
                    break
                else:
                    input_buffer.append(char)
                    print(char, end='', flush=True)  # 显示输入的字符
            
            # 短暂休眠避免占用过多 CPU
            time.sleep(0.01)
    except KeyboardInterrupt:
        should_quit = True
    except Exception as e:
        print(f"\n⚠️  输入监听异常: {e}")
        should_quit = True

def monitor_input_default():
    """
    非 Windows 平台的后台线程：监听终端输入
    """
    global should_quit
    
    print("\n💡 提示：在运行过程中输入 'quit' 可以停止程序运行")
    print("=" * 60 + "\n")
    
    try:
        while not should_quit:
            try:
                line = sys.stdin.readline()
                if line:
                    command = line.strip().lower()
                    if command == 'quit':
                        print("\n\n⚠️  收到退出指令，正在停止运行...")
                        should_quit = True
                        break
            except:
                pass
            time.sleep(0.1)
    except KeyboardInterrupt:
        should_quit = True

def start_input_monitor():
    """
    启动输入监听线程（自动选择适合当前平台的实现）
    """
    if os.name == 'nt':  # Windows
        monitor_thread = threading.Thread(target=monitor_input_windows, daemon=True)
    else:  # Linux/Mac
        monitor_thread = threading.Thread(target=monitor_input_default, daemon=True)
    
    monitor_thread.start()
    return monitor_thread

# 临时解决方案：绑定 hosts
# 10.64.84.182 openapi.seu.edu.cn
load_dotenv()

# === 完全禁用截图功能的环境变量配置 ===
# 增加点击事件超时时间，避免下载等待时的超时警告
os.environ['TIMEOUT_ClickElementEvent'] = '60.0'  # 从默认 15s 增加到 60s
os.environ['TIMEOUT_ScreenshotEvent'] = '60.0'    # 截图事件超时也增加
print("✅ 已配置环境变量：禁用截图功能，增加事件超时时间")

# 临时添加 host 映射,仅用在学校llm
# def add_host_mapping(host, ip):
#     """临时添加 host 映射到本地"""
#     try:
#         # 尝试解析域名，看是否已经配置
#         socket.gethostbyname(host)
#         print(f"✓ Host '{host}' 已配置")
#     except socket.gaierror:
#         print(f"⚠ 注意：需要在系统 hosts 文件中添加映射：{ip} {host}")
#         print(f"  Windows: C:\\Windows\\System32\\drivers\\etc\\hosts")
#         print(f"  以管理员身份运行记事本，添加：{ip} {host}")
#
# # 检查 host 配置
# add_host_mapping('openapi.seu.edu.cn', '10.64.84.182')

# === 导入工具函数 ===
def run_python_script(script_path: str, description: str = "脚本") -> bool:
    """
    运行 Python 脚本的辅助函数
    
    Args:
        script_path: 脚本的绝对路径
        description: 脚本描述
        
    Returns:
        是否成功执行
    """
    import subprocess
    import sys
    
    script = Path(script_path)
    
    if not script.exists():
        print(f"⚠️ 警告:{description}脚本不存在:{script}")
        return False
    
    try:
        # 使用当前 Python 解释器运行(避免环境问题)
        # 先以二进制模式捕获输出,避免编码错误
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            timeout=60,
            cwd=str(script.parent),  # 使用脚本所在目录作为工作目录
            env=os.environ.copy()  # 继承当前环境变量
        )
        
        # 手动解码输出:优先尝试 UTF-8,失败则用 GBK(Windows 中文环境)
        # errors='replace' 会用 替换无法解码的字符
        try:
            stdout = result.stdout.decode('gbk', errors='replace')
        except Exception:
            stdout = result.stdout.decode('utf-8', errors='replace')
        
        try:
            stderr = result.stderr.decode('gbk', errors='replace')
        except Exception:
            stderr = result.stderr.decode('utf-8', errors='replace')
        
        # 打印输出
        if stdout:
            print(f"\n📝 {description}输出:")
            print(stdout)
        
        if stderr:
            print(f"\n⚠️ {description}警告/错误:")
            print(stderr)
        
        if result.returncode == 0:
            print(f"\n✅ {description}完成!")
            return True
        else:
            print(f"\n❌ {description}失败,返回码:{result.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"\n❌ {description}超时(超过 60 秒)")
        return False
    except Exception as e:
        print(f"\n❌ 执行{description}时出错:{e}")
        return False

# === 导入 Pydantic ===
from pydantic import BaseModel

# === 定义参数模型 ===
class ExtractPageContentParams(BaseModel):
    """提取网页内容的参数模型"""
    output_filename: str = "page_content.md"  # 输出文件名(建议使用照片标题)
    output_dir: str = "D:\\desktop\\browser-use-main\\image"  # 输出目录(默认保存到 image 文件夹)
    format_type: str = "markdown"  # 格式类型: markdown, json, text
    information_file_path: str = "D:\\desktop\\browser-use-main\\Information.md"  # HTML代码块信息文件路径

class ExtractJSObjectParams(BaseModel):
    """提取JS对象内容的参数模型"""
    keyword: str = ""  # 要查找的关键词,如 analytics.item
    output_filename: str = "extracted_content.json"  # 输出文件名
    output_dir: str = "D:\\desktop\\browser-use-main\\image"  # 输出目录

# === 创建tools对象 ===
tools = Tools()
registry = tools.registry

# 注册自定义动作:提取网页内容并保存为文件，根据Information.md中指定的HTML代码块进行提取
@tools.action(description='提取当前网页源代码中符合Information.md文件中HTML代码块首尾行的部分并保存为文件', param_model=ExtractPageContentParams)
async def extract_page_to_markdown(params: ExtractPageContentParams, browser_session):
    """
    使用JavaScript提取网页源代码中符合Information.md文件中HTML代码块首尾行的部分
    
    参数说明:
    - output_filename: 输出文件名
    - output_dir: 输出目录
    - format_type: 格式类型，可选 'markdown'/'json'/'text'
    - information_file_path: Information.md文件路径，包含HTML代码块的首尾行信息
    """
    from pathlib import Path
    import re
    import json as json_module
        
    try:
        # 读取Information.md文件内容
        info_file_path = Path(params.information_file_path)
        if not info_file_path.exists():
            return ActionResult(error=f"Information.md文件不存在: {params.information_file_path}")
            
        info_content = info_file_path.read_text(encoding="utf-8")
            
        # 提取HTML代码块的开始和结束行
        html_blocks = re.findall(r"```html\n([\s\S]*?)```", info_content)
            
        if not html_blocks:
            return ActionResult(error="Information.md中没有找到HTML代码块")
            
        # 为每个HTML块构建查找模式
        search_patterns = []
        for block in html_blocks:
            lines = block.strip().split("\n")
            if len(lines) >= 1:
                # 获取第一行和最后一行作为搜索模式
                first_line = lines[0].strip()
                last_line = lines[-1].strip()
                if first_line and last_line:
                    search_patterns.append({
                        "start": first_line,
                        "end": last_line,
                        "full_block": block
                    })
            
        if not search_patterns:
            return ActionResult(error="未能从HTML代码块中提取有效的首尾行")
            
        # JavaScript代码：获取网页源代码并查找匹配的代码块
        js_code = f'''
        (function() {{
            try {{
                // 获取完整的页面HTML源代码
                const fullHtml = document.documentElement.outerHTML;
                    
                // 搜索模式，来自Information.md
                const searchPatterns = {json_module.dumps(search_patterns, ensure_ascii=False)};
                    
                const foundBlocks = [];
                    
                // 遍历每个搜索模式
                for (const pattern of searchPatterns) {{
                    // 转义特殊正则字符
                    const escapeRegExp = (string) => {{
                        return string.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\$&');
                    }};
                        
                    const startPattern = escapeRegExp(pattern.start);
                    const endPattern = escapeRegExp(pattern.end);
                        
                    // 创建正则表达式，使用非贪婪匹配
                    const regex = new RegExp(startPattern + '[\\\\s\\\\S]*?' + endPattern, 'gi');
                        
                    // 查找匹配项
                    let match;
                    while ((match = regex.exec(fullHtml)) !== null) {{
                        const matchedBlock = match[0];
                            
                        // 检查是否已存在相同的匹配块
                        const alreadyExists = foundBlocks.some(block => block.content === matchedBlock);
                        if (!alreadyExists) {{
                            foundBlocks.push({{
                                original_start: pattern.start,
                                original_end: pattern.end,
                                content: matchedBlock,
                                position: match.index
                            }});
                        }}
                    }}
                }}
                    
                return {{
                    success: true,
                    url: window.location.href,
                    title: document.title,
                    found_blocks: foundBlocks,
                    total_found: foundBlocks.length,
                    search_patterns: searchPatterns
                }};
            }} catch (error) {{
                return {{
                    success: false,
                    error: error.message,
                    stack: error.stack
                }};
            }}
        }})()
        '''
        
        # 执行JavaScript
        cdp_session = await browser_session.get_or_create_cdp_session()
        result = await cdp_session.cdp_client.send.Runtime.evaluate(
            params={'expression': js_code, 'returnByValue': True, 'awaitPromise': True},
            session_id=cdp_session.session_id
        )
        
        # 检查执行错误
        if result.get('exceptionDetails'):
            error_text = result['exceptionDetails'].get('text', '未知JS错误')
            return ActionResult(error=f'JavaScript执行失败: {error_text}')
        
        # 获取结果数据
        data = result.get('result', {}).get('value')
        if not data or not data.get('success'):
            error_msg = data.get('error', '未知错误') if data else '未获取到数据'
            return ActionResult(error=f'提取失败: {error_msg}')
        
        found_blocks = data.get('found_blocks', [])
        page_title = data.get('title', '')
        page_url = data.get('url', '')
        
        if not found_blocks:
            return ActionResult(error="在网页源代码中未找到匹配的HTML代码块")
        
        # 根据格式类型生成不同内容
        format_type = params.format_type.lower()
        
        if format_type == 'json':
            # JSON 格式：完整结构化数据
            file_content = json_module.dumps({
                'page_title': page_title,
                'url': page_url,
                'total_found_blocks': len(found_blocks),
                'found_blocks': found_blocks
            }, ensure_ascii=False, indent=2)
            file_ext = '.json'
            
        elif format_type == 'text':
            # 纯文本格式
            lines = [f"页面标题: {page_title}", f"URL: {page_url}", f"找到 {len(found_blocks)} 个匹配的HTML代码块", "=" * 80, ""]
            
            for i, block in enumerate(found_blocks, 1):
                lines.append(f"--- 匹配块 {i} ---")
                lines.append(f"原始起始行: {block.get('original_start', '')}")
                lines.append(f"原始结束行: {block.get('original_end', '')}")
                lines.append("提取的HTML代码:")
                lines.append(block.get('content', ''))
                lines.append("")
            
            file_content = "\n".join(lines)
            file_ext = '.txt'
            
        else:  # markdown (默认)
            # Markdown 格式
            md_content = f"# {page_title}\n\n"
            md_content += f"**URL**: {page_url}\n\n"
            md_content += f"**找到匹配的HTML代码块数量**: {len(found_blocks)}\n\n"
            md_content += "---\n\n"
            
            for i, block in enumerate(found_blocks, 1):
                md_content += f"## 匹配块 {i}\n\n"
                md_content += f"**原始起始行**: `{block.get('original_start', '')}`\n\n"
                md_content += f"**原始结束行**: `{block.get('original_end', '')}`\n\n"
                md_content += "**提取的HTML代码**:\n```html\n"
                md_content += f"{block.get('content', '')}\n"
                md_content += "```\n\n"
            
            file_content = md_content
            file_ext = '.md'
        
        # 清理文件名中的非法字符
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', params.output_filename)
        # 确保有正确的扩展名
        if not safe_filename.endswith(file_ext):
            # 移除旧扩展名，添加新扩展名
            safe_filename = re.sub(r'\.(md|json|txt)$', '', safe_filename) + file_ext
        
        # 构建完整路径（支持自定义目录）
        output_dir = Path(params.output_dir)
        output_path = output_dir / safe_filename
        
        # 创建目录（如果不存在）
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存到文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        success_msg = f"✅ 成功提取网页中匹配的HTML代码块并保存到: {output_path}\n格式: {format_type.upper()}\n共找到 {len(found_blocks)} 个匹配块"
        
        return ActionResult(
            extracted_content=success_msg,
            include_in_memory=True,
            long_term_memory=f'已将当前网页中匹配Information.md的HTML代码块提取并保存到 {safe_filename} (格式: {format_type})'
        )
        
    except Exception as e:
        error_msg = f'提取网页内容时出错: {str(e)}'
        return ActionResult(error=error_msg)

# 注册自定义动作:根据关键词提取JS对象内容
@tools.action(description='从Information.md中读取关键词,然后在页面源代码中查找类似 keyword = { ... } 的模式,提取{}中的完整内容并保存', param_model=ExtractJSObjectParams)
async def extract_js_object_by_keyword(params: ExtractJSObjectParams, browser_session):
    """
    根据Information.md中的关键词,在页面源代码中提取JS对象内容(如 analytics.item = { ... })
    
    参数说明:
    - keyword: 要查找的关键词,如 analytics.item。如果为空,则从Information.md中读取
    - output_filename: 输出文件名
    - output_dir: 输出目录
    """
    from pathlib import Path
    import json as json_module
    
    try:
        # 如果没有提供关键词,则从Information.md中读取
        if not params.keyword or params.keyword.strip() == "":
            info_file_path = Path(params.information_file_path)
            if not info_file_path.exists():
                return ActionResult(error=f"Information.md文件不存在: {params.information_file_path}")
            
            info_content = info_file_path.read_text(encoding="utf-8")
            
            # 从Information.md中提取可能的JS关键词(查找类似 "analytics.item", "window.data" 等模式)
            import re
            js_keywords = re.findall(r'([\w.]+)\s*=', info_content)
            
            # 去重并过滤掉HTML标签属性
            js_keywords = list(set([k for k in js_keywords if not k.startswith('<') and '.' in k]))
            
            if not js_keywords:
                return ActionResult(error="未从Information.md中找到JS关键词,请在参数中指定 keyword")
            
            # 使用第一个找到的关键词
            keyword = js_keywords[0]
        else:
            keyword = params.keyword.strip()
        
        # JavaScript代码:获取页面源代码并查找 keyword = { ... } 模式
        js_code = f'''
        (function() {{
            try {{
                const keyword = "{keyword}";
                const fullHtml = document.documentElement.outerHTML;
                
                // 转义关键词中的特殊字符
                const escapedKeyword = keyword.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\$&');
                
                // 匹配 keyword = {{ ... }} 模式,支持嵌套大括号
                const patterns = [
                    // 匹配 keyword = {{ ... }}
                    new RegExp(escapedKeyword + '\\s*=\\s*{{', 'gi'),
                    // 匹配 keyword:{{ ... }}
                    new RegExp(escapedKeyword + ':\\s*{{', 'gi')
                ];
                
                const foundObjects = [];
                
                for (const pattern of patterns) {{
                    let match;
                    while ((match = pattern.exec(fullHtml)) !== null) {{
                        const startIndex = match.index + match[0].length - 1; // {{ 的位置
                        
                        // 找到匹配的闭合大括号
                        let braceCount = 1;
                        let endIndex = startIndex + 1;
                        let inString = false;
                        let stringChar = '';
                        
                        while (endIndex < fullHtml.length && braceCount > 0) {{
                            const char = fullHtml[endIndex];
                            
                            // 处理字符串内的字符
                            if (!inString && (char === '"' || char === "'" || char === '`')) {{
                                inString = true;
                                stringChar = char;
                            }} else if (inString && char === stringChar && fullHtml[endIndex - 1] !== '\\') {{
                                inString = false;
                            }} else if (!inString) {{
                                if (char === '{{') braceCount++;
                                else if (char === '}}') braceCount--;
                            }}
                            
                            endIndex++;
                        }}
                        
                        if (braceCount === 0) {{
                            // 提取完整内容(包括 keyword = 部分)
                            const fullMatch = fullHtml.substring(match.index, endIndex);
                            // 只提取 {{ }} 中的内容
                            const objectContent = fullHtml.substring(startIndex, endIndex);
                            
                            // 检查是否已存在相同内容
                            const alreadyExists = foundObjects.some(obj => obj.content === objectContent);
                            if (!alreadyExists) {{
                                foundObjects.push({{
                                    keyword: keyword,
                                    position: match.index,
                                    full_match: fullMatch,
                                    content: objectContent
                                }});
                            }}
                        }}
                    }}
                }}
                
                return {{
                    success: true,
                    url: window.location.href,
                    title: document.title,
                    keyword: keyword,
                    found_objects: foundObjects,
                    total_found: foundObjects.length
                }};
            }} catch (error) {{
                return {{
                    success: false,
                    error: error.message,
                    stack: error.stack
                }};
            }}
        }})()
        '''
        
        # 执行JavaScript
        cdp_session = await browser_session.get_or_create_cdp_session()
        result = await cdp_session.cdp_client.send.Runtime.evaluate(
            params={'expression': js_code, 'returnByValue': True, 'awaitPromise': True},
            session_id=cdp_session.session_id
        )
        
        # 检查执行错误
        if result.get('exceptionDetails'):
            error_text = result['exceptionDetails'].get('text', '未知JS错误')
            return ActionResult(error=f'JavaScript执行失败: {error_text}')
        
        # 获取结果数据
        data = result.get('result', {}).get('value')
        if not data or not data.get('success'):
            error_msg = data.get('error', '未知错误') if data else '未获取到数据'
            return ActionResult(error=f'提取失败: {error_msg}')
        
        found_objects = data.get('found_objects', [])
        page_title = data.get('title', '')
        page_url = data.get('url', '')
        keyword = data.get('keyword', '')
        
        if not found_objects:
            return ActionResult(error=f"在网页源代码中未找到关键词 '{keyword}' 对应的对象")
        
        # 生成JSON格式的输出内容
        output_content = json_module.dumps({
            'page_title': page_title,
            'url': page_url,
            'keyword': keyword,
            'total_found': len(found_objects),
            'extracted_objects': found_objects
        }, ensure_ascii=False, indent=2)
        
        # 清理文件名中的非法字符
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', params.output_filename)
        if not safe_filename.endswith('.json'):
            safe_filename = re.sub(r'\.(md|txt)$', '', safe_filename) + '.json'
        
        # 构建完整路径
        output_dir = Path(params.output_dir)
        output_path = output_dir / safe_filename
        
        # 创建目录(如果不存在)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存到文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        success_msg = f"✅ 成功提取关键词 '{keyword}' 对应的JS对象内容并保存到: {output_path}\n共找到 {len(found_objects)} 个匹配对象"
        
        return ActionResult(
            extracted_content=success_msg,
            include_in_memory=True,
            long_term_memory=f'已从页面源代码中提取关键词 {keyword} 的JS对象内容并保存到 {safe_filename}'
        )
        
    except Exception as e:
        error_msg = f'提取JS对象内容时出错: {str(e)}'
        return ActionResult(error=error_msg)

async def main():
    # === 1. 从 task.md 文件读取任务描述 ===
    task_file = Path('D:\\desktop\\browser-use-main\\task.md')

    if not task_file.exists():
        print(f"❌ Task 文件不存在：{task_file}")
        raise FileNotFoundError(f"Task file not found: {task_file}")

    print(f"📄 从文件读取 task: {task_file}")
    with open(task_file, 'r', encoding='utf-8') as f:
        task = f.read().strip()
    print(f"✅ 成功读取 task，长度：{len(task)} 字符")

    # === 2. 运行 move_images.py 清空并转移图片 ===
    print("\n" + "=" * 60)
    print("📦 步骤 1: 执行图片迁移脚本...")
    print("=" * 60)
    
    move_script = Path('D:\\desktop\\browser-use-main\\move_images.py')
    run_python_script(str(move_script), "图片迁移")
    
    # 等待一下确保文件系统更新完成
    import time
    time.sleep(1)
    
    # # === 2.5. 运行 html_tool.py 生成 Information.md ===
    # print("\n" + "=" * 60)
    # print("🔧 步骤 2: 执行 HTML 分析工具生成 Information.md...")
    # print("=" * 60)
    #
    # html_tool_script = Path('D:\\desktop\\browser-use-main\\html_tool.py')
    # run_python_script(str(html_tool_script), "HTML分析工具")
    #
    # # 等待一下确保文件写入完成
    # time.sleep(1)
    
    # === 3. 创建浏览器与llm实例 ===
    browser = Browser(
        # use_cloud=True,  # Use a stealth browser on Browser Use Cloud
        args=[
            '--user-data-dir=D:\\desktop\\browser-use-main\\browser_profile'
        ],
        headless=False,
        enable_default_extensions=False,  # 禁用扩展以避免干扰
    )

    api_key = '9c2fcf1e-afc3-4dc4-8b7e-636cdac31519'
    base_url = 'https://openapi.seu.edu.cn/v1'

    llm = ChatOpenAI(
        model='qwen3.5-397b-a17b',
        api_key=api_key,
        base_url=base_url,
        temperature=0.0
    )
    #llm = ChatBrowserUse(),  # 官方llm，需写在agent中

    # === 4. 创建 Agent（完全禁用截图，使用 JS 提取） ===
    agent = Agent(
        task=task,  # 使用从.md 文件读取的 task
        llm=llm,
        #llm=ChatBrowserUse(),#官方llm
        # llm=ChatOpenAI(
        #     model=os.getenv("SEU_MODEL_NAME"),
        #     api_key=os.getenv("SEU_API_KEY"),
        #     base_url=os.getenv("SEU_BASE_URL"),
        # ),#学校qwen3.5llm，需在agent外设定
        # llm=ChatGoogle(model='gemini-3-flash-preview'),
        # llm=ChatAnthropic(model='claude-sonnet-4-6'),
        browser=browser,
        tools=tools,  # 添加自定义工具（包括 extract_page_to_markdown）
        use_vision=False,  # 完全关闭视觉识别和截图
        max_failures=3,  # 降低失败重试次数
        max_actions_per_step=3,  # 允许每步执行更多动作提高效率
        step_timeout=180,  # 增加单步超时时间
        llm_timeout=120,  # 增加 LLM 超时时间
        file_system_path='D:\\desktop\\browser-use-main',
        available_file_paths=[  # 允许访问的文件路径
            r'D:\desktop\browser-use-main\image',  # image 目录（允许读写该目录下所有文件）
            r'D:\desktop\browser-use-main\browseruse_agent_data',  # agent数据目录
            r'D:\desktop\browser-use-main\Information.md',  # Information.md 文件
            r'D:\tmp\browser-use-downloads-c75e39b0',  # 默认下载目录
            r'D:\desktop\browser-use-main\source.html',  # 源代码文件
            r'D:\desktop\browser-use-main\title.txt',  # 标题文件
            r'D:\desktop\browser-use-main\rename_record.txt',  # 重命名记录
        ],
    )
    
    # === 5. 运行 agent ===
    print("\n🚀 开始执行任务...")
    
    # 启动输入监听线程
    input_thread = start_input_monitor()
    
    try:
        history = await agent.run(max_steps=1000)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断执行 (Ctrl+C)")
        return None
    
    # 检查是否是因为 quit 命令而停止
    if should_quit:
        print("\n🛑 程序已被用户手动停止")
        print("\n=== 任务统计（截至停止时）===")
        print(f"总步数：{history.number_of_steps()}")
        print(f"总耗时：{history.total_duration_seconds():.2f} 秒")
        print(f"访问 URL 数：{len(history.urls())}")
        return history

    # === 添加验证逻辑 ===
    image_dir = Path('D:\\desktop\\browser-use-main\\image')

    print("\n=== 下载结果验证 ===")

    # 检查两个可能的下载目录
    download_dirs = [
        Path('D:\\desktop\\browser-use-main\\image'),
        Path('D:\\tmp\\browser-use-downloads-c75e39b0')
    ]
    
    all_image_files = []
    for img_dir in download_dirs:
        if img_dir.exists():
            # 查找所有 TIFF 和 PNG 文件
            tiff_files = list(img_dir.glob('*.tif*'))
            png_files = list(img_dir.glob('image_*.png'))
            all_image_files.extend(tiff_files)
            all_image_files.extend(png_files)
            print(f"✓ 目录 {img_dir} 中找到 {len(tiff_files) + len(png_files)} 个文件")
        else:
            print(f"ℹ️ 目录不存在：{img_dir}")
    
    if all_image_files:
        print(f"\n总共找到 {len(all_image_files)} 个下载的文件:")
        for img_file in sorted(all_image_files):
            file_size = img_file.stat().st_size
            print(f"  - {img_file.name}: {file_size:,} 字节")
            if file_size == 0:
                print(f"  ⚠️ 警告：{img_file.name} 文件大小为 0")
    else:
        print("❌ 未找到任何下载的文件")
        
        # 检查 title.txt 是否存在
        title_file = Path('D:\\desktop\\browser-use-main\\title.txt')
        if title_file.exists():
            with open(title_file, 'r', encoding='utf-8') as f:
                title_count = len([line for line in f if line.strip()])
            print(f"✓ title.txt 存在，包含 {title_count} 个标题")
        else:
            print(f"⚠️ title.txt 不存在")

    # 检查历史中的错误
    errors = history.errors()
    if any(errors):
        error_count = sum(1 for e in errors if e is not None)
        print(f"\n⚠️ 执行过程中出现 {error_count} 个错误")


    # 输出最终统计
    print(f"\n=== 任务统计 ===")
    print(f"总步数：{history.number_of_steps()}")
    print(f"总耗时：{history.total_duration_seconds():.2f} 秒")
    print(f"访问 URL 数：{len(history.urls())}")
    
    # === 6. 自动执行重命名脚本 ===
    print("\n" + "=" * 60)
    print("🔄 步骤 3: 执行图片重命名脚本...")
    print("=" * 60)
    
    rename_script = Path('D:\\desktop\\browser-use-main\\rename_images.py')
    
    # 使用改进的脚本执行函数
    success = run_python_script(str(rename_script), "图片重命名")
    
    if success:
        # 显示重命名后的文件
        renamed_files = list(image_dir.glob('*.png'))
        if renamed_files:
            print(f"\n📁 重命名后的文件列表 (共 {len(renamed_files)} 个):")
            for f in sorted(renamed_files):
                if not f.name.startswith('image_'):
                    print(f"  - {f.name}")
        
        # 显示重命名记录文件
        record_file = Path('D:\\desktop\\browser-use-main\\rename_record.txt')
        if record_file.exists():
            print(f"\n📄 重命名记录已保存到：{record_file}")
    else:
        print("💡 请检查错误信息并手动执行：python rename_images.py")

    return history

if __name__ == "__main__":
    asyncio.run(main())