#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO11 目标检测工具
基于 Ultralytics YOLO11 实现图像目标检测
输入: 本地图像路径
输出: 检测到的类别和边界框坐标 (xyxy格式)
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import cv2
import numpy as np
from ultralytics import YOLO
import json

class YOLODetector:
    """YOLO11目标检测器"""
    
    def __init__(self, model_path: str = "yolo11n.pt", confidence: float = 0.5, device: str = "auto"):
        """
        初始化YOLO检测器
        
        Args:
            model_path: YOLO模型路径，默认为yolo11n.pt
            confidence: 置信度阈值，默认0.5
            device: 设备类型，'auto', 'cpu', 'cuda'等
        """
        self.model_path = model_path
        self.confidence = confidence
        self.device = device
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """加载YOLO模型"""
        try:
            print(f"🔄 正在加载YOLO模型: {self.model_path}")
            self.model = YOLO(self.model_path)
            print(f"✅ 模型加载成功！设备: {self.device}")
        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            sys.exit(1)
    
    def detect_image(self, image_path: str) -> List[Dict]:
        """
        检测单张图像中的目标
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            检测结果列表，每个元素包含类别、置信度和边界框信息
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图像文件不存在: {image_path}")
        
        try:
            # 执行检测
            results = self.model(image_path, conf=self.confidence, device=self.device)
            
            detections = []
            
            for result in results:
                # 获取检测框信息
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
            
            return detections
            
        except Exception as e:
            print(f"❌ 检测过程中发生错误: {e}")
            return []
    
    def detect_batch(self, image_paths: List[str]) -> Dict[str, List[Dict]]:
        """
        批量检测多张图像
        
        Args:
            image_paths: 图像文件路径列表
            
        Returns:
            字典，键为图像路径，值为检测结果列表
        """
        results = {}
        
        for i, image_path in enumerate(image_paths, 1):
            print(f"🔄 处理图像 {i}/{len(image_paths)}: {os.path.basename(image_path)}")
            detections = self.detect_image(image_path)
            results[image_path] = detections
            
            # 显示检测结果摘要
            if detections:
                print(f"   ✅ 检测到 {len(detections)} 个目标")
                for det in detections:
                    print(f"      - {det['class_name']}: {det['confidence']:.2f}")
            else:
                print(f"   ⚠️  未检测到目标")
        
        return results
    
    def visualize_detections(self, image_path: str, output_path: Optional[str] = None) -> str:
        """
        可视化检测结果
        
        Args:
            image_path: 输入图像路径
            output_path: 输出图像路径，如果为None则自动生成
            
        Returns:
            输出图像路径
        """
        if output_path is None:
            base_name = Path(image_path).stem
            output_path = f"{base_name}_detected.jpg"
        
        try:
            # 执行检测并保存结果图像
            results = self.model(image_path, conf=self.confidence, device=self.device)
            
            # 保存带标注的图像
            for result in results:
                result.save(output_path)
            
            print(f"✅ 可视化结果已保存到: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"❌ 可视化过程中发生错误: {e}")
            return ""

def main():
    """主函数 - 命令行接口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="YOLO11目标检测工具")
    parser.add_argument("image_path", help="输入图像路径")
    parser.add_argument("--model", default="yolo11n.pt", help="YOLO模型路径 (默认: yolo11n.pt)")
    parser.add_argument("--confidence", type=float, default=0.5, help="置信度阈值 (默认: 0.5)")
    parser.add_argument("--device", default="auto", help="设备类型 (默认: auto)")
    parser.add_argument("--output", help="输出JSON文件路径")
    parser.add_argument("--visualize", action="store_true", help="生成可视化结果图像")
    parser.add_argument("--batch", help="批量处理目录路径")
    
    args = parser.parse_args()
    
    print("🤖 YOLO11 目标检测工具")
    print("=" * 50)
    
    # 创建检测器
    detector = YOLODetector(
        model_path=args.model,
        confidence=args.confidence,
        device=args.device
    )
    
    if args.batch:
        # 批量处理模式
        print(f"📁 批量处理目录: {args.batch}")
        
        # 支持的图像格式
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
        
        # 获取所有图像文件
        image_paths = []
        for ext in image_extensions:
            image_paths.extend(Path(args.batch).glob(f"*{ext}"))
            image_paths.extend(Path(args.batch).glob(f"*{ext.upper()}"))
        
        if not image_paths:
            print("❌ 目录中未找到图像文件")
            return
        
        print(f"📊 找到 {len(image_paths)} 个图像文件")
        
        # 执行批量检测
        results = detector.detect_batch([str(p) for p in image_paths])
        
        # 保存结果
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"💾 批量检测结果已保存到: {args.output}")
        
    else:
        # 单图像处理模式
        print(f"🖼️  处理图像: {args.image_path}")
        
        # 执行检测
        detections = detector.detect_image(args.image_path)
        
        # 显示结果
        if detections:
            print(f"\n🎯 检测到 {len(detections)} 个目标:")
            print("-" * 60)
            for i, det in enumerate(detections, 1):
                print(f"{i:2d}. 类别: {det['class_name']:15s} | "
                      f"置信度: {det['confidence']:.3f} | "
                      f"边界框: [{det['bbox']['x1']:.1f}, {det['bbox']['y1']:.1f}, "
                      f"{det['bbox']['x2']:.1f}, {det['bbox']['y2']:.1f}]")
        else:
            print("⚠️  未检测到任何目标")
        
        # 保存结果到JSON文件
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(detections, f, ensure_ascii=False, indent=2)
            print(f"💾 检测结果已保存到: {args.output}")
        
        # 生成可视化图像
        if args.visualize:
            output_path = detector.visualize_detections(args.image_path)
            if output_path:
                print(f"🖼️  可视化图像已保存到: {output_path}")

def detect_single_image(image_path: str, model_path: str = "yolo11n.pt", 
                       confidence: float = 0.5, device: str = "auto") -> List[Dict]:
    """
    便捷函数：检测单张图像
    
    Args:
        image_path: 图像路径
        model_path: 模型路径
        confidence: 置信度阈值
        device: 设备类型
        
    Returns:
        检测结果列表
    """
    detector = YOLODetector(model_path, confidence, device)
    return detector.detect_image(image_path)

if __name__ == "__main__":
    main()
