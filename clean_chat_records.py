#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
聊天记录清理脚本
功能：
1. 读取 chat_record 目录中的所有 JSON 文件
2. 删除 content 字段包含 "error" 的项
3. 基于 "Error: {name} is not a valid tool" 模式，删除对应的 tool_calls.name 项
"""

import json
import os
import re
from typing import List, Dict, Any
from datetime import datetime

# 聊天记录目录
CHAT_RECORD_DIR = "chat_record"

def clean_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    清理消息列表，删除包含错误的项
    
    Args:
        messages: 消息列表
        
    Returns:
        清理后的消息列表
    """
    cleaned_messages = []
    invalid_tools = set()  # 存储无效的工具名称
    
    # 第一遍：收集所有无效的工具名称
    for message in messages:
        content = message.get('content', '')
        if isinstance(content, str) and 'error' in content.lower():
            # 检查是否是 "Error: {name} is not a valid tool" 模式
            error_pattern = r'Error:\s*([^\\s]+)\s*is\s*not\s*a\s*valid\s*tool'
            match = re.search(error_pattern, content, re.IGNORECASE)
            if match:
                invalid_tool_name = match.group(1)
                invalid_tools.add(invalid_tool_name)
                print(f"🔍 发现无效工具: {invalid_tool_name}")
    
    print(f"📋 总共发现 {len(invalid_tools)} 个无效工具: {list(invalid_tools)}")
    
    # 第二遍：删除包含错误的项和无效工具调用
    for message in messages:
        content = message.get('content', '')
        
        # 跳过包含 error 的消息
        if isinstance(content, str) and 'error' in content.lower():
            print(f"🗑️  删除包含错误的消息: {content[:100]}...")
            continue
        
        # 检查 tool_calls 中的无效工具
        tool_calls = message.get('tool_calls', [])
        if tool_calls:
            valid_tool_calls = []
            for tool_call in tool_calls:
                tool_name = tool_call.get('name', '')
                if tool_name in invalid_tools:
                    print(f"🗑️  删除无效工具调用: {tool_name}")
                else:
                    valid_tool_calls.append(tool_call)
            
            # 如果所有工具调用都被删除，跳过整个消息
            if not valid_tool_calls and tool_calls:
                print(f"🗑️  删除所有工具调用都被清理的消息")
                continue
            
            # 更新消息中的 tool_calls
            message['tool_calls'] = valid_tool_calls
        
        cleaned_messages.append(message)
    
    return cleaned_messages

def clean_chat_record_file(filepath: str) -> bool:
    """
    清理单个聊天记录文件
    
    Args:
        filepath: 文件路径
        
    Returns:
        是否成功清理
    """
    try:
        # 读取原始文件
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        original_messages_count = len(data.get('messages', []))
        print(f"📄 处理文件: {os.path.basename(filepath)}")
        print(f"   原始消息数量: {original_messages_count}")
        
        # 清理消息
        if 'messages' in data:
            data['messages'] = clean_messages(data['messages'])
            cleaned_messages_count = len(data['messages'])
            
            print(f"   清理后消息数量: {cleaned_messages_count}")
            print(f"   删除了 {original_messages_count - cleaned_messages_count} 条消息")
            
            # 更新统计信息
            data['total_messages'] = cleaned_messages_count
            
            # 添加清理信息到 metadata
            if 'metadata' not in data:
                data['metadata'] = {}
            data['metadata']['cleaned_at'] = datetime.now().isoformat()
            data['metadata']['original_message_count'] = original_messages_count
            data['metadata']['cleaned_message_count'] = cleaned_messages_count
        
        # 备份原文件
        backup_path = filepath + '.backup'
        if not os.path.exists(backup_path):
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"   备份文件: {os.path.basename(backup_path)}")
        
        # 保存清理后的文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 文件清理完成: {os.path.basename(filepath)}")
        return True
        
    except Exception as e:
        print(f"❌ 清理文件失败 {filepath}: {e}")
        return False

def main():
    """主函数"""
    print("🧹 开始清理聊天记录...")
    print(f"📁 目标目录: {CHAT_RECORD_DIR}")
    
    # 检查目录是否存在
    if not os.path.exists(CHAT_RECORD_DIR):
        print(f"❌ 目录不存在: {CHAT_RECORD_DIR}")
        return
    
    # 获取所有 JSON 文件
    json_files = [f for f in os.listdir(CHAT_RECORD_DIR) if f.endswith('.json')]
    
    if not json_files:
        print("📭 没有找到 JSON 文件")
        return
    
    print(f"📊 找到 {len(json_files)} 个 JSON 文件")
    
    # 统计信息
    total_files = len(json_files)
    success_count = 0
    error_count = 0
    
    # 处理每个文件
    for filename in json_files:
        filepath = os.path.join(CHAT_RECORD_DIR, filename)
        print(f"\n{'='*60}")
        
        if clean_chat_record_file(filepath):
            success_count += 1
        else:
            error_count += 1
    
    # 输出总结
    print(f"\n{'='*60}")
    print("📈 清理完成统计:")
    print(f"   总文件数: {total_files}")
    print(f"   成功清理: {success_count}")
    print(f"   清理失败: {error_count}")
    print(f"   成功率: {success_count/total_files*100:.1f}%")
    
    if success_count > 0:
        print("\n💡 提示:")
        print("   - 原文件已备份为 .backup 文件")
        print("   - 可以手动检查清理结果")
        print("   - 如需恢复，可以将 .backup 文件重命名回原文件名")

if __name__ == "__main__":
    main()
