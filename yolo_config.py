#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO11 检测工具配置文件
包含各种预设配置和模型信息
"""

# 可用的YOLO11模型
YOLO_MODELS = {
    "yolo11n": {
        "file": "yolo11n.pt",
        "size": "nano",
        "description": "最小最快模型，适合实时检测",
        "params": "2.7M",
        "speed": "最快"
    },
    "yolo11s": {
        "file": "yolo11s.pt", 
        "size": "small",
        "description": "小型模型，平衡速度和精度",
        "params": "9.7M",
        "speed": "快"
    },
    "yolo11m": {
        "file": "yolo11m.pt",
        "size": "medium", 
        "description": "中型模型，较好的精度",
        "params": "20.9M",
        "speed": "中等"
    },
    "yolo11l": {
        "file": "yolo11l.pt",
        "size": "large",
        "description": "大型模型，高精度",
        "params": "26.2M", 
        "speed": "慢"
    },
    "yolo11x": {
        "file": "yolo11x.pt",
        "size": "extra-large",
        "description": "最大模型，最高精度",
        "params": "58.8M",
        "speed": "最慢"
    }
}

# 默认配置
DEFAULT_CONFIG = {
    "model": "yolo11n.pt",
    "confidence": 0.5,
    "device": "auto",
    "input_size": 640,
    "max_det": 1000,
    "agnostic_nms": False,
    "half": False,
    "dnn": False,
    "data": None,
    "verbose": True
}

# 设备配置
DEVICE_CONFIG = {
    "auto": "自动选择最佳设备",
    "cpu": "使用CPU",
    "cuda": "使用CUDA GPU",
    "cuda:0": "使用第一个GPU",
    "cuda:1": "使用第二个GPU",
    "mps": "使用Apple Silicon GPU (M1/M2)"
}

# 支持的图像格式
SUPPORTED_FORMATS = {
    "images": [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"],
    "videos": [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"]
}

# COCO数据集类别名称 (YOLO11默认支持)
COCO_CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake",
    "chair", "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop",
    "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]

# 性能基准 (在COCO数据集上的表现)
PERFORMANCE_BENCHMARKS = {
    "yolo11n": {"mAP50": 37.5, "mAP50-95": 25.3, "speed_cpu": 0.99, "speed_gpu": 0.15},
    "yolo11s": {"mAP50": 44.3, "mAP50-95": 30.7, "speed_cpu": 1.20, "speed_gpu": 0.18},
    "yolo11m": {"mAP50": 49.8, "mAP50-95": 35.4, "speed_cpu": 1.83, "speed_gpu": 0.28},
    "yolo11l": {"mAP50": 52.2, "mAP50-95": 37.4, "speed_cpu": 2.39, "speed_gpu": 0.35},
    "yolo11x": {"mAP50": 53.2, "mAP50-95": 38.3, "speed_cpu": 3.53, "speed_gpu": 0.48}
}

def get_model_info(model_name: str) -> dict:
    """
    获取模型信息
    
    Args:
        model_name: 模型名称
        
    Returns:
        模型信息字典
    """
    return YOLO_MODELS.get(model_name, {})

def get_default_config() -> dict:
    """获取默认配置"""
    return DEFAULT_CONFIG.copy()

def get_supported_formats() -> dict:
    """获取支持的格式"""
    return SUPPORTED_FORMATS.copy()

def print_model_comparison():
    """打印模型对比信息"""
    print("📊 YOLO11 模型对比")
    print("=" * 80)
    print(f"{'模型':<12} {'大小':<8} {'参数':<8} {'速度':<8} {'mAP50':<8} {'mAP50-95':<8}")
    print("-" * 80)
    
    for model_name, info in YOLO_MODELS.items():
        perf = PERFORMANCE_BENCHMARKS.get(model_name, {})
        print(f"{model_name:<12} {info['size']:<8} {info['params']:<8} {info['speed']:<8} "
              f"{perf.get('mAP50', 'N/A'):<8} {perf.get('mAP50-95', 'N/A'):<8}")
    
    print("\n💡 选择建议:")
    print("- yolo11n: 实时应用，移动设备")
    print("- yolo11s: 平衡性能和速度")
    print("- yolo11m: 一般应用推荐")
    print("- yolo11l: 高精度需求")
    print("- yolo11x: 最高精度，离线处理")

def get_optimal_model(use_case: str) -> str:
    """
    根据使用场景推荐最佳模型
    
    Args:
        use_case: 使用场景 ('realtime', 'balanced', 'accuracy', 'mobile')
        
    Returns:
        推荐的模型名称
    """
    recommendations = {
        "realtime": "yolo11n",
        "balanced": "yolo11s", 
        "accuracy": "yolo11l",
        "mobile": "yolo11n",
        "offline": "yolo11x"
    }
    
    return recommendations.get(use_case, "yolo11n")

if __name__ == "__main__":
    print("🔧 YOLO11 配置信息")
    print("=" * 50)
    
    print_model_comparison()
    
    print(f"\n📋 默认配置:")
    config = get_default_config()
    for key, value in config.items():
        print(f"  {key}: {value}")
    
    print(f"\n🎯 使用场景推荐:")
    scenarios = ["realtime", "balanced", "accuracy", "mobile", "offline"]
    for scenario in scenarios:
        model = get_optimal_model(scenario)
        print(f"  {scenario}: {model}")
    
    print(f"\n📁 支持的图像格式:")
    formats = get_supported_formats()
    print(f"  图像: {', '.join(formats['images'])}")
    print(f"  视频: {', '.join(formats['videos'])}")
