#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的服务器测试脚本
"""

import sys
import importlib.util

def check_dependencies():
    """检查必要的依赖"""
    required = [
        "fastapi",
        "langchain_openai", 
        "langgraph",
        "ultralytics",
        "python_dotenv"
    ]
    
    missing = []
    for package in required:
        if not importlib.util.find_spec(package.replace('-', '_')):
            missing.append(package)
    
    if missing:
        print("❌ 缺少依赖:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\n安装命令:")
        print(f"pip install {' '.join(missing)}")
        return False
    
    print("✅ 所有核心依赖已安装")
    return True

def check_asgi_servers():
    """检查ASGI服务器"""
    servers = ["uvicorn", "hypercorn"]
    available = []
    
    for server in servers:
        if importlib.util.find_spec(server):
            available.append(server)
    
    if available:
        print(f"✅ 可用的ASGI服务器: {', '.join(available)}")
        return True
    else:
        print("❌ 未找到ASGI服务器")
        print("安装命令: pip install uvicorn")
        return False

def test_import():
    """测试导入backend_api模块"""
    try:
        print("🔍 测试导入backend_api模块...")
        import backend_api
        print("✅ backend_api模块导入成功")
        
        # 测试app对象
        if hasattr(backend_api, 'app'):
            print("✅ FastAPI app对象存在")
        
        # 测试初始化函数
        if hasattr(backend_api, 'initialize_graph'):
            print("✅ initialize_graph函数存在")
        
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def main():
    print("🧪 LangGraph后端服务器测试")
    print("=" * 40)
    
    success = True
    
    # 检查依赖
    if not check_dependencies():
        success = False
    
    print()
    
    # 检查ASGI服务器
    if not check_asgi_servers():
        success = False
    
    print()
    
    # 测试导入
    if not test_import():
        success = False
    
    print()
    print("=" * 40)
    
    if success:
        print("🎉 所有测试通过！")
        print("可以运行: python backend_api.py")
    else:
        print("❌ 测试失败，请先解决上述问题")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
