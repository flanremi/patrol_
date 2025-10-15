#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO Agent Tool for LangGraph
一个简单的YOLO检测工具，可以直接集成到LangGraph工作流中
"""

import os
from typing import List, Dict, Any, Optional
from ultralytics import YOLO
import json
from langchain_core.tools import tool


class YOLOAgentTool:
    """YOLO检测工具 - 专为LangGraph设计"""
    
    def __init__(self, model_path: str = "yolo11n.pt", confidence: float = 0.5):
        """
        初始化YOLO工具
        
        Args:
            model_path: YOLO模型路径，默认yolo11n.pt
            confidence: 置信度阈值，默认0.5
        """
        self.model_path = model_path
        self.confidence = confidence
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载YOLO模型"""
        try:
            self.model = YOLO(self.model_path)
        except Exception as e:
            print(f"❌ YOLO模型加载失败: {e}")
            self.model = None
    
    def detect_objects(self, image_path: str) -> Dict[str, Any]:
        """
        检测图像中的对象 - LangGraph工具入口
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            检测结果字典，包含状态、消息和检测数据
        """
        if not self.model:
            return {
                "status": "error",
                "message": "YOLO模型未正确加载",
                "detections": []
            }
        
        if not os.path.exists(image_path):
            return {
                "status": "error", 
                "message": f"图像文件不存在: {image_path}",
                "detections": []
            }
        
        try:
            # 执行检测
            results = self.model(image_path, conf=self.confidence)
            
            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for i in range(len(boxes)):
                        # 获取边界框坐标 (xyxy格式)
                        xyxy = boxes.xyxy[i].cpu().numpy()
                        
                        # 获取置信度
                        conf = boxes.conf[i].cpu().numpy()
                        
                        # 获取类别ID和名称
                        cls_id = int(boxes.cls[i].cpu().numpy())
                        cls_name = self.model.names[cls_id]
                        
                        detection = {
                            "class_id": cls_id,
                            "class_name": cls_name,
                            "confidence": float(conf),
                            "bbox": {
                                "x1": float(xyxy[0]),
                                "y1": float(xyxy[1]), 
                                "x2": float(xyxy[2]),
                                "y2": float(xyxy[3])
                            }
                        }
                        detections.append(detection)
            
            # 生成人类可读的检测摘要
            if detections:
                summary = f"检测到 {len(detections)} 个对象: "
                class_counts = {}
                for det in detections:
                    class_name = det['class_name']
                    class_counts[class_name] = class_counts.get(class_name, 0) + 1
                
                summary += ", ".join([f"{name}({count})" for name, count in class_counts.items()])
            else:
                summary = "未检测到任何对象"
            
            return {
                "status": "success",
                "message": summary,
                "detections": detections,
                "count": len(detections)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"检测过程中发生错误: {str(e)}",
                "detections": []
            }

# 全局YOLO工具实例
_yolo_tool = None

def get_yolo_tool(model_path: str = "yolo11n.pt", confidence: float = 0.5) -> YOLOAgentTool:
    """
    获取YOLO工具实例 (单例模式)
    
    Args:
        model_path: 模型路径
        confidence: 置信度阈值
        
    Returns:
        YOLOAgentTool实例
    """
    global _yolo_tool
    if _yolo_tool is None:
        _yolo_tool = YOLOAgentTool(model_path, confidence)
    return _yolo_tool

@tool
def yolo_detect_tool(image_path: str) -> str:
    """
    一个用来识别图像中有多少目标的目标工具
    
    Args:
        image_path: 图像文件路径
        
    Returns:
        检测结果的JSON字符串
    """
    tool = get_yolo_tool()
    result = tool.detect_objects(image_path)
    return json.dumps(result, ensure_ascii=False, indent=2)

# LangGraph工具定义
YOLO_TOOL = {
    "name": "yolo_detect",
    "description": "使用YOLO11检测图像中的对象，返回类别和边界框信息",
    "parameters": {
        "type": "object",
        "properties": {
            "image_path": {
                "type": "string",
                "description": "要检测的图像文件路径"
            }
        },
        "required": ["image_path"]
    },
    "function": yolo_detect_tool
}

# 便捷函数
def detect_image(image_path: str) -> Dict[str, Any]:
    """
    便捷函数：检测图像中的对象
    
    Args:
        image_path: 图像文件路径
        
    Returns:
        检测结果字典
    """
    tool = get_yolo_tool()
    return tool.detect_objects(image_path)

# 测试函数
def test_yolo_tool():
    """测试YOLO工具"""
    print("🧪 测试YOLO工具")
    print("=" * 40)
    
    # 测试工具初始化
    tool = get_yolo_tool()
    print(f"✅ 工具初始化成功，模型: {tool.model_path}")
    
    # 测试检测功能 (需要提供实际图像路径)
    test_image = "test_image.jpg"
    if os.path.exists(test_image):
        result = tool.detect_objects(test_image)
        print(f"📊 检测结果: {result['message']}")
        if result['detections']:
            print("🎯 检测到的对象:")
            for det in result['detections']:
                print(f"  - {det['class_name']}: {det['confidence']:.3f}")
    else:
        print(f"⚠️  测试图像不存在: {test_image}")
        print("请将图像文件重命名为 'test_image.jpg' 进行测试")

if __name__ == "__main__":
    test_yolo_tool()
