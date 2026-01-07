import requests
import json
import os
import time
import base64
from urllib3.exceptions import InsecureRequestWarning
from PIL import Image
import re
from bs4 import BeautifulSoup


requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# -------------------------- 核心配置 --------------------------
TENANT_ID = "6064398b5b9520fa3cfe8090"
PROJECT_ID = "42095753da5a500edb73d8c098"
PROJECT_SPACE_ID = "42095753da5a500edb73d8c098"
USER_ID = "69363a48f95578dee4f984b3"
ORGANIZATION_ID = "6064398b5b9520fa3cfe8090"
WORKITEM_TYPE_ID = "37da3a07df4d08aef2e3b393"
DEFAULT_STATUS_ID = "df20e9a65f57eab0bbfe946fbd"  # 默认状态ID
# SPRINT_IDS_DEFAULT = ["565109778f6ca44653bc6bd66f"]

# 优先级/严重程度/状态/处理人映射
PRIORITY_MAP = {
    "最高": "a2ef76837be379de92a236ea96",
    "较高": "4fc7fdc14893848bcae822d4ef",
    "一般": "7956b23e9d26f0e97d3274fa86",
    "较低": "9810eccc48e35cb80852ef717e"
}
SERIOUS_LEVEL_MAP = {
    "致命": "4125fbce94f1404accde51af17",
    "严重": "221d2b06bc3b0eef0c8ededb03",
    "一般": "8c1eca1f6ee1882dec8789b25a",
    "建议": "8cffbfa06b1faa2ebf3c2807bd"
}
STATUS_MAP = {
    "修复完成": "11ba1ffa50f92fee3f529c666a",
    "再次打开": "30",
    "挂起": "df20e9a65f57eab0bbfe946fbd",
    "处理中": "100010",
    "关闭": "100085",
    "新提交": "a0b2e1cb84ed8289494bb7fb14",
    "保持观察": "11ba1ffa50f92fee3f529c666a"}

ASSIGNEE_MAP = {
    "刘伟科": "60c1919aaa6381038e49362e",
    "查智文": "60643979e5ccc4277855ad35",
    "许铭宏": "692ff7aea9444359a9152c2d",
    "王强": "60c1919a750bbcd1c05a0e12",
    "俞尚": "69081fe719f260d93e5da3ff",
    "Minisform-测试组": "692ff7aea9444359a9152c2d",
    "曹欣哲": "68999586a9444359a91de631",
    "阮贤炽": "69363bedccafad1056b41876",
    "何琪": "69363a48f95578dee4f984b3",
    "袁旺": "695b26cb50168a3e7ea36267"
}

# 有效Cookie和CSRF Token
COOKIE = "**"
APIPOST_CSRF_TOKEN = "**"
CREATE_BUG_URL = "https://devops.aliyun.com/projex/api/workitem/workitem?_input_charset=utf-8"


# -------------------------- 工具函数 --------------------------
def get_csrf_token_from_cookie():
    try:
        return APIPOST_CSRF_TOKEN
    except Exception as e:
        try:
            xsrf_token = COOKIE.split("XSRF-TOKEN=")[1].split(";")[0].strip()
            return xsrf_token
        except IndexError:
            try:
                cr_token = COOKIE.split("cr_token=")[1].split(";")[0].strip()
                return cr_token
            except IndexError:
                print("❌ 无法从Cookie提取CSRF Token")
                return None


def build_bug_description(html_str):
    if html_str.startswith("p>"):
        html_str = "<" + html_str
    soup = BeautifulSoup(html_str, "html.parser")
    for p_tag in soup.find_all("p"):
        if not p_tag.get_text(strip=True):
            p_tag.decompose()
    html_parts = []
    jsonml_nodes = []
    current_time = int(time.time())
    for tag in soup.contents:
        if tag.name is None:
            continue
        if tag.name == "p":
            text_content = tag.get_text(strip=True)
            if not text_content:
                continue
            text_html = text_content.replace('\n', '<br>')
            html_parts.append(f'<p style="text-align:left;line-height:1.6"><span>{text_html}</span></p>')
            jsonml_nodes.append(["p", {"style": "text-align:left;line-height:1.6"},
                                 ["span", {"data-type": "text"}, ["span", {"data-type": "leaf"}, text_content]]])
        elif tag.name == "img":
            img_src = tag.get("src", "")
            img_alt = tag.get("alt", "未命名图片")
            img_style = tag.get("style", "text-align:center;")
            img_size = tag.get("size", "0")
            if not img_src:
                continue
            align_style = "text-align:center;margin:16px 0;"
            if "text-align" in img_style:
                align_style = img_style + ";margin:16px 0;"
            img_html = f'<p style="{align_style}"><img src="{img_src}" style="width:auto;height:auto;max-width:100%" /></p>'
            html_parts.append(img_html.strip())
            jsonml_nodes.append(["p", {"style": align_style}, ["img",
                                                               {"id": f"img_{current_time}_{int(time.time() * 1000)}",
                                                                "name": img_alt, "size": img_size, "width": "auto",
                                                                "height": "auto", "rotation": 0, "src": img_src}]])
    final_html = f'<article class="4ever-article">{"".join(html_parts)}</article>'
    final_jsonml = ["root", {}] + jsonml_nodes
    return {"htmlValue": final_html.strip(), "jsonMLValue": final_jsonml}


def build_comment_content(comment_text):
    comment_html = comment_text.replace('\n', '<br>')
    rich_content = {
        "htmlValue": f'<article class="4ever-article"><p style="text-align:left;line-height:1.6">{comment_html}</p></article>',
        "jsonMLValue": ["root", {}, ["p", {"style": "text-align:left;line-height:1.6"},
                                     ["span", {"data-type": "text"}, ["span", {"data-type": "leaf"}, comment_text]]]]
    }
    return rich_content


def parse_comments(comments_list):
    """仅过滤空评论，完全保留原始内容"""
    if not comments_list:
        return []
    return [c.strip() for c in comments_list if c and c.strip()]


# -------------------------- 创建Bug函数 --------------------------
def create_single_bug(bug_dict, max_retry=2):
    bug_title = bug_dict.get("title", "")
    if not bug_title:
        print(f"❌ Bug标题为空")
        return None

    # 读取字段（兼容多字段名）
    original_html = bug_dict.get("description", "")
    created_by = bug_dict.get("created_by", "未知用户")
    created_at = bug_dict.get("created_at", 0)
    created_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(created_at)) if created_at else "未知时间"

    # 核心修复：兼容PingCode可能的链接字段名
    bug_url = bug_dict.get("bug_url", "") or bug_dict.get("web_url", "") or bug_dict.get("workitem_url", "") or ""
    bug_url = bug_url.strip()

    # 核心修复：兼容PingCode可能的状态字段名
    state_name = bug_dict.get("state_name", "") or bug_dict.get("status", "") or ""
    state_name = state_name.strip()

    # 拼接描述（确保链接必显）
    extra_html = f'''<hr style="margin:20px 0;border:none;border-top:1px solid #eee;" />
<p style="text-align:left;line-height:1.6">由 {created_by} 在 {created_time} 创建</p>
<p style="text-align:left;line-height:1.6">pingcode链接：<a href="{bug_url}" target="_blank" style="color:#1890ff;text-decoration:underline;">{bug_url if bug_url else "无"}</a></p>'''
    html_content = original_html + extra_html

    bug_desc = build_bug_description(html_content)
    if not bug_desc:
        print(f"❌ {bug_title}：构造描述失败")
        return None

    csrf_token = get_csrf_token_from_cookie()
    if not csrf_token:
        print(f"❌ {bug_title}：缺少CSRF Token")
        return None

    priority = bug_dict.get("priority", "一般")
    priority_id = PRIORITY_MAP.get(priority, PRIORITY_MAP["一般"])
    severity = bug_dict.get("severity", "一般")
    severity_id = SERIOUS_LEVEL_MAP.get(severity, SERIOUS_LEVEL_MAP["一般"])

    # 状态映射（严格匹配）
    status_id = STATUS_MAP.get(state_name, DEFAULT_STATUS_ID)
    print(f"【状态映射】Bug标题：{bug_title} | state_name='{state_name}' → 云效状态ID='{status_id}'")
    if status_id == DEFAULT_STATUS_ID and state_name != "":
        print(f"⚠️ 注意：state_name='{state_name}'未在STATUS_MAP中配置，已使用默认状态")

    assignee = bug_dict.get("assignee", "")
    assignee_id = ASSIGNEE_MAP.get(assignee, USER_ID) if ASSIGNEE_MAP.get(assignee) != "测试组的云效ID" else USER_ID

    bug_data = {
        "subject": bug_title,
        "description": json.dumps(bug_desc, ensure_ascii=False),
        "descriptionFormat": "RICHTEXT",
        "categoryIdentifier": "Bug",
        "workitemTypeIdentifier": WORKITEM_TYPE_ID,
        "workitemType": WORKITEM_TYPE_ID,
        "category": "Bug",
        "spaceIdentifier": PROJECT_SPACE_ID,
        "space": PROJECT_SPACE_ID,
        "spaceType": "Project",
        "organizationIdentifier": ORGANIZATION_ID,
        "tenantId": TENANT_ID,
        "projectId": PROJECT_ID,
        "statusIdentifier": status_id,
        "logicalStatus": "NORMAL",
        "assignedTo": assignee_id,
        "creator": USER_ID,
        "modifier": USER_ID,
        # "sprint": SPRINT_IDS_DEFAULT,
        "fieldValueList": [{"fieldIdentifier": "priority", "value": priority_id},
                           {"fieldIdentifier": "seriousLevel", "value": severity_id}],
        "identifierPath": None,
        "parentIdentifier": None,
        "directory": None,
        "finishTime": None,
        "cloneFrom": None,
        "createWorkitemRelationInfo": {},
        "serialNumber": None,
        "gmtCreate": None,
        "gmtModified": None,
        "csrfToken": csrf_token
    }

    headers = {
        "Cookie": COOKIE,
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://devops.aliyun.com/",
        "X-CSRF-Token": csrf_token,
        "last-workspace": "6064398b5b9520fa3cfe8090",
        "priority": "u=1, i",
        "web-last-workspace": "6064398b5b9520fa3cfe8090",
        "x-requested-with": "XMLHttpRequest"
    }

    # 超时重试
    for retry in range(max_retry + 1):
        try:
            response = requests.post(CREATE_BUG_URL, headers=headers, data=json.dumps(bug_data, ensure_ascii=False),
                                     timeout=30, verify=False)
            response.encoding = "utf-8"
            result = response.json()

            if response.status_code == 200 and result.get("code") == 200:
                bug_identifier = result["result"].get("identifier", "未知")
                bug_internal_id = result["result"].get("id", "未知")
                print(f"🎉 {bug_title} 创建成功 | 业务标识：{bug_identifier}（内部ID：{bug_internal_id}）")
                return bug_identifier
            else:
                error_msg = result.get("errorMsg", "未知错误")
                if retry < max_retry:
                    print(f"⚠️ {bug_title} 创建失败（第{retry + 1}次重试）：{error_msg}，5秒后重试...")
                    time.sleep(5)
                else:
                    print(f"❌ {bug_title} 创建失败（已重试{max_retry + 1}次）：{error_msg}")
                    return None
        except Exception as e:
            error_info = str(e)
            if retry < max_retry:
                print(f"⚠️ {bug_title} 创建异常（第{retry + 1}次重试）：{error_info}，5秒后重试...")
                time.sleep(5)
            else:
                print(f"❌ {bug_title} 创建异常（已重试{max_retry + 1}次）：{error_info}")
                return None


def create_single_comment(bug_identifier, comment_text="", comment_user_id=USER_ID, max_retry=3, retry_delay=3):
    if not bug_identifier or not comment_text:
        print(f"❌ 跳过添加评论（ID/内容为空）")
        return False
    comment_content = build_comment_content(comment_text)
    csrf_token = get_csrf_token_from_cookie()
    if not csrf_token:
        print(f"❌ 缺少CSRF Token")
        return False
    COMMENT_URL = f"https://devops.aliyun.com/projex/api/workitem/workitem/{bug_identifier}/comment?_input_charset=utf-8"
    comment_data = {
        "content": json.dumps(comment_content, ensure_ascii=False),
        "contentFormat": "RICHTEXT",
        "csrfToken": csrf_token,
        "parentId": None,
        "spaceIdentifier": PROJECT_SPACE_ID,
        "projectId": PROJECT_ID,
        "tenantId": TENANT_ID,
        "creator": comment_user_id,
        "modifier": comment_user_id
    }
    headers = {
        "Cookie": COOKIE,
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
        "Referer": f"https://devops.aliyun.com/workitem/{bug_identifier}",
        "X-CSRF-Token": csrf_token,
        "last-workspace": "6064398b5b9520fa3cfe8090",
        "priority": "u=1, i",
        "web-last-workspace": "6064398b5b9520fa3cfe8090",
        "x-requested-with": "XMLHttpRequest"
    }
    for retry in range(max_retry):
        try:
            response = requests.post(COMMENT_URL, headers=headers, data=json.dumps(comment_data, ensure_ascii=False),
                                     timeout=15, verify=False)
            result = response.json()
            if response.status_code == 200 and result.get("code") == 200:
                print(f"✅ Bug[{bug_identifier}] 评论添加成功（评论者：{comment_user_id}）")
                return True
            else:
                error_msg = result.get("errorMsg", f"状态码：{response.status_code}")
                if retry < max_retry - 1:
                    print(f"⚠️ Bug[{bug_identifier}] 评论失败（第{retry + 1}次），{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                else:
                    print(f"❌ Bug[{bug_identifier}] 评论失败（重试{max_retry}次）：{error_msg}")
                    return False
        except Exception as e:
            if retry < max_retry - 1:
                print(f"⚠️ Bug[{bug_identifier}] 评论异常（第{retry + 1}次），{retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                print(f"❌ Bug[{bug_identifier}] 评论异常：{str(e)}")
                return False


# -------------------------- 批量创建函数 --------------------------
def batch_create_bugs(bugs_list, retry_tag="首次"):
    success_count = 0
    fail_list = []
    total_count = len(bugs_list)
    print(f"\n🚀 {retry_tag}批量创建Bug（共{total_count}个）")
    print("-" * 80)

    for idx, bug_dict in enumerate(bugs_list, 1):
        bug_title = bug_dict.get("title", f"未命名Bug_{idx}")
        print(f"\n[{idx}/{total_count}] 处理：{bug_title}")

        bug_identifier = create_single_bug(bug_dict)
        if not bug_identifier:
            print(f"[{idx}/{total_count}] ❌ 跳过")
            fail_list.append(bug_dict)
            continue

        success_count += 1
        print(f"[{idx}/{total_count}] ⏳ 等待5秒（同步云效数据）...")
        time.sleep(5)

        comments_list = bug_dict.get("comments", [])
        parsed_comments = parse_comments(comments_list)
        if parsed_comments:
            print(f"[{idx}/{total_count}] 📝 开始添加{len(parsed_comments)}条评论...")
            for comment_idx, comment_content in enumerate(parsed_comments, 1):
                # 打印原始完整内容（确认没被修改）
                print(f"[{idx}/{total_count}] 评论{comment_idx} 原始内容：{comment_content}")
                # 直接传入原始内容，评论人ID用默认（或你想匹配的话也可以，但内容绝对不修改）
                create_single_comment(bug_identifier, comment_content, USER_ID)
                time.sleep(1)
        else:
            print(f"[{idx}/{total_count}] 📝 无评论")

    print("-" * 80)
    print(f"\n🏁 {retry_tag}完成！成功{success_count}/{total_count}")

    if fail_list:
        print(f"\n❌ {retry_tag}失败的Bug列表（共{len(fail_list)}个）：")
        for i, fail_bug in enumerate(fail_list, 1):
            print(f"  {i}. {fail_bug.get('title', '未命名Bug')} | PingCode链接：{fail_bug.get('bug_url', '无')}")

    return success_count, fail_list


# -------------------------- 执行入口 --------------------------
if __name__ == "__main__":
    if PROJECT_ID == "替换为你的云效项目ID" or not COOKIE:
        print("❌ 请填写PROJECT_ID和Cookie")
        exit()

    # # 第一步：先打印PingCode原始数据（找到正确字段名）
    # print("🔍 第一步：获取PingCode原始数据，定位正确字段名...")
    # # 请先替换debug_pingcode_raw_data函数中的PINGCODE_TOKEN，再取消注释运行
    # # debug_pingcode_raw_data()

    # 第二步：从PingCode获取Bug数据（替换原PingCodeClient逻辑，兼容多字段）
    print("\n🔍 第二步：从PingCode获取Bug数据...")
    try:
        from utils.ping_code_utils import PingCodeClient

        pcc = PingCodeClient()
        search_data = {
            "addon_setting_id": "6847a64c4c9434fbbce54bcf",
            "criteria": {
                "sort_by": "updated_at",
                "sort_direction": -1,
                "conditions": [
                    {"operation": 6, "property_key": "iteration", "value": ["6959e353c7330c2b08ab9761"], "logic": 1}
                ],
            },
            "columns": [
                "identifier", "title", "description",
                "state", "status",  # 状态相关字段
                "url", "web_url", "workitem_url",  # 链接相关字段
                "priority", "severity", "assignee", "created_by", "created_at", "comments"
            ],
            "is_brief": 1,
            "pi": 0,
            "ps": 1000,
        }
        bugs = pcc.get_format_bug_info(search_data)
        print(f"✅ 成功获取{len(bugs)}个Bug数据")

        # 字段映射（兼容多字段名）
        # 字段映射（直接读取返回数据中的state_name和bug_url）
        mapped_bugs = []
        for bug in bugs:
            # 直接读取返回数据中已有的state_name和bug_url（无需兼容其他字段）
            raw_state = bug.get("state_name", "").strip()
            raw_url = bug.get("bug_url", "").strip()

            # 调试日志：确认拿到的状态和链接
            print(f"【调试】Bug标题：{bug.get('title')} | PingCode状态：'{raw_state}' | PingCode链接：'{raw_url}'")

            mapped_bug = {
                "identifier": bug.get("identifier", ""),
                "title": bug.get("title", ""),
                "description": bug.get("description", ""),
                "state_name": raw_state,
                "priority": bug.get("priority", "一般"),
                "severity": bug.get("severity", "一般"),
                "assignee": bug.get("assignee", ""),
                "created_by": bug.get("created_by", "未知用户"),
                "created_at": bug.get("created_at", 0),
                "bug_url": raw_url,
                "comments": bug.get("comments", [])
            }
            mapped_bugs.append(mapped_bug)

        # 批量创建
        first_success, fail_list = batch_create_bugs(mapped_bugs, retry_tag="首次")

        # 重试失败的Bug
        if fail_list:
            print(f"\n🔄 开始重试失败的Bug（共{len(fail_list)}个）...")
            time.sleep(10)
            retry_success, final_fail_list = batch_create_bugs(fail_list, retry_tag="重试")

            total_success = first_success + retry_success
            total_count = len(mapped_bugs)
            print(f"\n📊 最终结果：")
            print(f"   总数量：{total_count}")
            print(f"   首次成功：{first_success}")
            print(f"   重试成功：{retry_success}")
            print(f"   最终成功：{total_success}")
            print(f"   最终失败：{len(final_fail_list)}")

            if final_fail_list:
                print(f"\n❌ 最终同步失败的Bug列表：")
                for i, fail_bug in enumerate(final_fail_list, 1):
                    print(f"  {i}. 标题：{fail_bug.get('title', '未命名Bug')}")
                    print(f"     PingCode链接：{fail_bug.get('bug_url', '无')}")
                    print(f"     状态：{fail_bug.get('state_name', '未知')}")
        else:
            print("\n🎉 所有Bug都同步成功，无需重试！")
    except ImportError:
        print("❌ 缺少PingCodeClient模块，请确保utils/ping_code_utils.py存在且可导入")
    except Exception as e:
        print(f"❌ 执行异常：{str(e)}")
