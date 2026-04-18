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

# 临时解决方案：绑定 hosts
# 10.64.84.182 openapi.seu.edu.cn
load_dotenv()

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
from browser_use import Agent, Browser, ChatOpenAI, ActionResult
from browser_use import Tools
from pydantic import BaseModel
import asyncio
import os
import re
import json
from pathlib import Path
from typing import Optional


# === 定义参数模型 ===
class AnalyzeHTMLParams(BaseModel):
    """分析 HTML 文件的参数"""
    html_file_path: str = "D:\\desktop\\browser-use-main\\source.html"  # HTML 文件路径
    output_info_path: str = "D:\\desktop\\browser-use-main\\info.md"  # 输出提示词文件路径


class UpdateExtractToolParams(BaseModel):
    """更新提取工具参数的参数"""
    info_file_path: str = "D:\\desktop\\browser-use-main\\info.md"  # info.md 文件路径


class SmartExtractPageContentParams(BaseModel):
    """智能提取网页内容的参数（基于 info.md）"""
    output_filename: str = "page_content.md"  # 输出文件名
    output_dir: str = "D:\\desktop\\browser-use-main\\image"  # 输出目录
    format_type: str = "markdown"  # 格式类型: markdown, json, text
    info_file_path: str = "D:\\desktop\\browser-use-main\\info.md"  # info.md 文件路径


# === 创建tools对象 ===
tools = Tools()
registry = tools.registry

# 注册自定义动作:提取网页内容并保存为MD文件
# === 工具 2: 根据 info.md 更新提取工具参数 ===
@tools.action(
    description='读取 info.md 文件，解析其中的提示词，返回优化后的提取参数配置',
    param_model=UpdateExtractToolParams
)
async def update_extract_tool_from_info(params: UpdateExtractToolParams, browser_session=None):
    """
    读取 info.md 文件，提取其中的关键提示词和选择器
    返回可用于配置 extract_page_to_markdown 工具的参数
    """
    try:
        info_path = Path(params.info_file_path)

        if not info_path.exists():
            return ActionResult(error=f'info.md 文件不存在: {params.info_file_path}')

        # 读取 info.md
        with open(info_path, 'r', encoding='utf-8') as f:
            info_content = f.read()

        print(f"📄 已读取 info.md: {info_path}")

        # 解析关键信息
        extracted_config = parse_info_md(info_content)

        # 生成配置摘要
        config_summary = f"""
✅ 已从 info.md 提取配置信息:

**识别的模式数量**: {extracted_config.get('pattern_count', 0)}
**主要选择器**: {', '.join(extracted_config.get('selectors', [])[:5])}
**关键词列表**: {', '.join(extracted_config.get('keywords', [])[:10])}
**JavaScript 代码片段**: {'已提取' if extracted_config.get('js_code') else '未找到'}

**建议的提取策略**:
- 优先使用 CSS 选择器: {extracted_config.get('primary_selector', 'N/A')}
- 关注的数据属性: {', '.join(extracted_config.get('data_attrs', []))}
- 目标元素类型: {', '.join(extracted_config.get('target_elements', []))}
"""

        # 将配置保存到全局变量或返回给调用者
        # 这里我们返回配置信息，实际使用时可以存储到环境变量或配置文件
        return ActionResult(
            extracted_content=config_summary.strip(),
            include_in_memory=True,
            long_term_memory=f'已从 info.md 提取 {extracted_config.get("pattern_count", 0)} 个模式的配置信息'
        )

    except Exception as e:
        error_msg = f'读取 info.md 时出错: {str(e)}'
        print(f"❌ {error_msg}")
        return ActionResult(error=error_msg)


def parse_info_md(info_content: str) -> dict:
    """解析 info.md 文件，提取关键配置信息"""
    config = {
        'pattern_count': 0,
        'selectors': [],
        'keywords': [],
        'js_code': None,
        'primary_selector': '',
        'data_attrs': [],
        'target_elements': []
    }

    # 提取 CSS 选择器
    selector_matches = re.findall(r'\*\*CSS 选择器\*\*:\s*`([^`]+)`', info_content)
    config['selectors'] = selector_matches
    config['pattern_count'] = len(selector_matches)

    # 提取主要选择器（第一个）
    if selector_matches:
        config['primary_selector'] = selector_matches[0]

    # 提取关键词（从模式类型中提取）
    type_matches = re.findall(r'### 模式 \d+: (\w+)', info_content)
    config['keywords'] = type_matches

    # 提取 JavaScript 代码
    js_match = re.search(r'```javascript\n(.*?)\n```', info_content, re.DOTALL)
    if js_match:
        config['js_code'] = js_match.group(1)

    # 提取数据属性
    attr_matches = re.findall(r'- `(data-\w+)`', info_content)
    config['data_attrs'] = list(set(attr_matches))

    # 提取目标元素类型
    element_matches = re.findall(r'tag:\s*(\w+)', info_content)
    config['target_elements'] = list(set(element_matches))

    return config


# === 工具 3: 智能提取网页内容（基于 info.md）===
@tools.action(
    description='智能提取网页内容，根据 info.md 中的提示词精准提取目标信息',
    param_model=SmartExtractPageContentParams
)
async def smart_extract_page_content(params: SmartExtractPageContentParams, browser_session):
    """
    智能提取网页内容：
    1. 读取 info.md 获取提取提示词
    2. 根据提示词构建精准的 JavaScript 提取代码
    3. 只提取提示词对应的内容
    4. 保存到指定文件
    """
    try:
        from pathlib import Path
        import json as json_module

        # 步骤 1: 读取 info.md
        info_path = Path(params.info_file_path)
        if not info_path.exists():
            return ActionResult(error=f'info.md 文件不存在: {params.info_file_path}')

        with open(info_path, 'r', encoding='utf-8') as f:
            info_content = f.read()

        print(f"📄 已读取 info.md，开始智能提取...")

        # 步骤 2: 解析提示词，构建 JavaScript 提取代码
        js_code = build_smart_js_code(info_content)

        # 步骤 3: 执行 JavaScript 提取
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

        items = data.get('data', [])
        page_title = data.get('pageTitle', '未知标题')
        page_url = data.get('url', '未知URL')

        print(f"✅ 成功提取 {len(items)} 个内容项")

        # 步骤 4: 根据格式类型生成内容
        format_type = params.format_type.lower()

        if format_type == 'json':
            file_content = json_module.dumps({
                'page_title': page_title,
                'url': page_url,
                'total_items': len(items),
                'items': items
            }, ensure_ascii=False, indent=2)
            file_ext = '.json'

        elif format_type == 'text':
            lines = [f"页面标题: {page_title}", f"URL: {page_url}", "=" * 80, ""]

            for item in items:
                if item.get('type') == 'image_meta':
                    lines.append(f"[图片元数据]")
                    lines.append(f"属性: {item.get('property', '')}")
                    lines.append(f"URL: {item.get('content', '')}")
                    lines.append("")

                elif item.get('type') == 'image_link':
                    lines.append(f"[图片链接]")
                    lines.append(f"类型: {item.get('type_attr', '')}")
                    lines.append(f"URL: {item.get('href', '')}")
                    lines.append("")

                elif item.get('type') == 'container':
                    lines.append(f"[图片容器]")
                    lines.append(f"选择器: {item.get('selector', '')}")
                    lines.append(f"内容预览: {item.get('preview', '')[:200]}")
                    lines.append("")

            file_content = "\n".join(lines)
            file_ext = '.txt'

        else:  # markdown (默认)
            md_content = f"# {page_title}\n\n"
            md_content += f"**URL**: {page_url}\n\n"
            md_content += f"**提取项数**: {len(items)}\n\n"
            md_content += "---\n\n"

            for item in items:
                if item.get('type') == 'image_meta':
                    md_content += f"## 图片元数据\n\n"
                    md_content += f"**属性**: `{item.get('property', '')}`\n\n"
                    md_content += f"**URL**: {item.get('content', '')}\n\n"

                elif item.get('type') == 'image_link':
                    md_content += f"## 图片资源链接\n\n"
                    md_content += f"**格式**: {item.get('type_attr', '')}\n\n"
                    md_content += f"**URL**: {item.get('href', '')}\n\n"

                elif item.get('type') == 'container':
                    md_content += f"## 图片容器\n\n"
                    md_content += f"**选择器**: `{item.get('selector', '')}`\n\n"
                    md_content += f"**内容预览**:\n```html\n"
                    md_content += item.get('preview', '')[:500]
                    md_content += "\n```\n\n"

            file_content = md_content
            file_ext = '.md'

        # 步骤 5: 保存文件
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', params.output_filename)
        if not safe_filename.endswith(file_ext):
            safe_filename = re.sub(r'\.(md|json|txt)$', '', safe_filename) + file_ext

        output_dir = Path(params.output_dir)
        output_path = output_dir / safe_filename
        output_dir.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(file_content)

        success_msg = f"✅ 智能提取完成并保存到: {output_path}\n格式: {format_type.upper()}\n共提取 {len(items)} 个精准匹配的内容项"

        return ActionResult(
            extracted_content=success_msg,
            include_in_memory=True,
            long_term_memory=f'已使用 info.md 提示词智能提取网页内容到 {safe_filename}'
        )

    except Exception as e:
        error_msg = f'智能提取网页内容时出错: {str(e)}'
        print(f"❌ {error_msg}")
        return ActionResult(error=error_msg)


def build_smart_js_code(info_content: str) -> str:
    """根据 info.md 内容构建精准的 JavaScript 提取代码"""

    # 解析 info.md 中的选择器和模式
    selectors = re.findall(r'\*\*CSS 选择器\*\*:\s*`([^`]+)`', info_content)
    has_og_image = 'meta_og_image' in info_content
    has_link_alternate = 'link_alternate_image' in info_content
    has_containers = any(cls in info_content for cls in ['item-image', 'photo-container', 'image-wrapper'])

    # 构建 JavaScript 代码
    js_code = """
    (function() {
        try {
            const results = [];
            const seenUrls = new Set();

            // 辅助函数：添加内容（避免重复）
            function addContent(type, data) {
                const key = data.content || data.href || data.url || JSON.stringify(data);
                if (!seenUrls.has(key)) {
                    seenUrls.add(key);
                    results.push({ type, ...data });
                }
            }
    """

    # 根据 info.md 中的模式动态添加提取逻辑
    if has_og_image:
        js_code += """
            // 1. 提取 og:image meta 标签（高优先级）
            document.querySelectorAll('meta[property^="og:image"]').forEach(meta => {
                const property = meta.getAttribute('property');
                const content = meta.getAttribute('content');
                if (content) {
                    addContent('image_meta', {
                        property: property,
                        content: content,
                        priority: 'high'
                    });
                }
            });
        """

    if has_link_alternate:
        js_code += """
            // 2. 提取 link alternate image（高质量图片资源）
            document.querySelectorAll("link[rel='alternate'][type^='image/']").forEach(link => {
                const href = link.href;
                const typeAttr = link.getAttribute('type');
                if (href) {
                    addContent('image_link', {
                        href: href,
                        type_attr: typeAttr,
                        priority: 'high'
                    });
                }
            });
        """

    # 添加自定义选择器
    if selectors:
        js_code += "\n            // 3. 提取自定义选择器匹配的元素\n"
        for selector in selectors[:5]:  # 最多使用 5 个选择器
            js_code += f"""
            try {{
                const elements_{selectors.index(selector)} = document.querySelectorAll('{selector}');
                if (elements_{selectors.index(selector)}.length > 0) {{
                    elements_{selectors.index(selector)}.forEach(el => {{
                        addContent('custom_selector', {{
                            selector: '{selector}',
                            tag: el.tagName.toLowerCase(),
                            text: el.textContent.trim().substring(0, 200),
                            html_preview: el.outerHTML.substring(0, 300)
                        }});
                    }});
                }}
            }} catch(e) {{}}
            """

    if has_containers:
        js_code += """
            // 4. 提取常见图片容器
            const containerSelectors = ['.item-image', '.photo-container', '.image-wrapper', '#main-image', '.primary-image'];
            containerSelectors.forEach(selector => {
                try {
                    const elements = document.querySelectorAll(selector);
                    if (elements.length > 0) {
                        elements.forEach(el => {
                            addContent('container', {
                                selector: selector,
                                tag: el.tagName.toLowerCase(),
                                preview: el.outerHTML.substring(0, 500),
                                child_count: el.children.length
                            });
                        });
                    }
                } catch(e) {}
            });
        """

    # 添加通用图片提取
    js_code += """
            // 5. 提取所有 img 标签（备用）
            document.querySelectorAll('img').forEach((img, idx) => {
                const src = img.src || img.getAttribute('data-src') || '';
                const alt = img.alt || '';
                if (src && !src.startsWith('data:')) {
                    addContent('image_tag', {
                        index: idx + 1,
                        src: src,
                        alt: alt,
                        width: img.width,
                        height: img.height
                    });
                }
            });

            // 获取页面基本信息
            const pageTitle = document.title || '无标题';
            const pageUrl = window.location.href;

            return {
                success: true,
                pageTitle: pageTitle,
                url: pageUrl,
                data: results,
                totalItems: results.length,
                stats: {
                    imageMeta: results.filter(r => r.type === 'image_meta').length,
                    imageLinks: results.filter(r => r.type === 'image_link').length,
                    containers: results.filter(r => r.type === 'container').length,
                    customSelectors: results.filter(r => r.type === 'custom_selector').length,
                    imageTags: results.filter(r => r.type === 'image_tag').length
                }
            };

        } catch (error) {
            return {
                success: false,
                error: error.message,
                stack: error.stack
            };
        }
    })()
    """

    return js_code


async def main():
    # === 1. 创建llm实例 ===
    api_key = '9c2fcf1e-afc3-4dc4-8b7e-636cdac31519'
    base_url = 'https://openapi.seu.edu.cn/v1'

    llm1 = ChatOpenAI(
        model='qwen3.5-397b-a17b',
        api_key=api_key,
        base_url=base_url,
        temperature=0.0
    )

    # === 2. 创建 Agent（学习html源码） ===
    agent = Agent(
        task=r"打开D:\desktop\browser-use-main\source.html文件，识别其中与主图片有关的信息所在的代码块，并将它们的首行和末行写入D:\desktop\browser-use"
             r"-main\info.md",
        tools=tools,  # 添加自定义工具
        llm = llm1,
        use_vision=False,  # 完全关闭视觉识别和截图
        max_failures=3,  # 降低失败重试次数
        max_actions_per_step=3,  # 允许每步执行更多动作提高效率
        step_timeout=180,  # 增加单步超时时间
        llm_timeout=120,  # 增加 LLM 超时时间
        file_system_path='D:\\desktop\\browser-use-main',
        available_file_paths=[  # 允许访问的文件路径
            r'D:\desktop\browser-use-main\image',
            r'D:\desktop\browser-use-main\browseruse_agent_data\info.txt',
            r'D:\desktop\browser-use-main\browseruse_agent_data\title.txt',
            r'D:\tmp\browser-use-downloads-c75e39b0'  # 添加默认下载目录
        ],
    )

    # === 3. 运行 agent ===
    print("\n🚀 开始执行任务...")
    history = await agent.run(max_steps=1000)

    import time
    time.sleep(2)

    # 任务 2: 读取 info.md 并显示配置
    print("\n" + "=" * 60)
    print("⚙️  任务 2: 读取 info.md 并显示配置信息")
    print("=" * 60)

    # 直接调用工具函数（不需要 agent）
    from pathlib import Path
    info_path = Path('D:\\desktop\\browser-use-main\\info.md')

    if info_path.exists():
        with open(info_path, 'r', encoding='utf-8') as f:
            info_content = f.read()

        print(f"\n📄 info.md 内容预览:")
        print("-" * 60)
        print(info_content[:500])
        print("...")
        print("-" * 60)

        # 解析配置
        config = parse_info_md(info_content)
        print(f"\n✅ 解析的配置信息:")
        print(f"   模式数量: {config['pattern_count']}")
        print(f"   选择器: {', '.join(config['selectors'][:3])}")
        print(f"   关键词: {', '.join(config['keywords'][:5])}")
    else:
        print(f"⚠️ info.md 不存在，请先运行任务 1")

    print("\n" + "=" * 60)
    print("💡 使用说明")
    print("=" * 60)
    print("""
    现在你可以使用以下工具：

    1. analyze_html_for_image - 分析新的 HTML 文件生成 info.md
    2. update_extract_tool_from_info - 读取 info.md 获取配置
    3. smart_extract_page_content - 使用 info.md 提示词智能提取网页内容

    示例代码：
    ```python
    # 对类似结构的网页进行智能提取
    agent = Agent(
        task="使用 smart_extract_page_content 工具提取当前页面的图片信息",
        llm=llm,
        browser=browser,
        tools=tools,
        use_vision=False,
    )
    await agent.run()
    ```
    """)

    return history


if __name__ == "__main__":
    asyncio.run(main())