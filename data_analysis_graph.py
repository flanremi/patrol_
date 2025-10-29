#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import os
from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv
import json
import timm
from typing import Dict
from langgraph_helper import common_llm

load_dotenv()

import cv2
import numpy as np
from ultralytics import YOLO
from ultralytics.utils.plotting import Colors
import torch, torchvision
from image_enhancement_tool import enhance_net_nopool
from skimage.morphology import skeletonize
import math
import torch
from torchvision import transforms
import segmentation_models_pytorch as smp
from tqdm import tqdm
from PIL import Image
# from skimage.io import imread, imsave
# from skimage.color import rgb2gray
# from skimage.morphology import skeletonize
# from skimage.util import img_as_ubyte
# from skimage.measure import label, regionprops
# from scipy.stats import linregress

# 定义状态类型
class State(TypedDict):
    """对话状态，使用add_messages自动处理消息列表更新"""
    messages: Annotated[list, add_messages]


# ==================== 数据预处理工具定义 ====================

@tool
def image_enhancement(content: str) -> str:
    """
    图像增强工具，对原始图像进行对比度、亮度调整和降噪处理
    
    Args:
        content: 输入的原始图像数据描述
        
    Returns:
        str: 图像增强结果的JSON字符串
    """
    def get_image_params(image):

        # 转换为灰度图（简化计算）
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        # 1. 亮度：灰度值均值（归一化到0-1）
        brightness = np.mean(gray) / 255.0
        
        # 2. 对比度：灰度值标准差（归一化到0-1，理论最大约127.5/255）
        contrast = np.std(gray) / 255.0
        contrast = min(contrast * 2, 1.0)  # 缩放至0-1范围（增强区分度）
        
        # 3. 噪声水平：用高斯滤波残差估计（归一化到0-1）
        # 高斯滤波去除信号，残差即为噪声
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        noise = np.mean(np.abs(gray - blurred))  # 噪声强度
        noise = min(noise / 50, 1.0)  # 归一化（假设最大噪声为50）

        # 4. 动态范围分析
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256]) 
        dynamic_range = np.sum(hist > 0) / 256.0

        image_params = {
            "brightness":brightness,
            "contrast":contrast,
            "noise_level":noise,
            "dynamic_range":dynamic_range
        }

        return image_params

    print("image_enhancement工具被调用")

    # ----------------------------
    # 读取拍摄图像并分析
    # ----------------------------
    input_image_path = "./images/input1.png"
    image = cv2.imread(input_image_path) # 暂时忽略输入content的内容，直接从本地指定路径加载图像
    original_params = get_image_params(image) # 这个结果本应是规划与策略智能体的输出结果

    # ----------------------------
    # 进行图像增强，有传统图像处理和基于深度学习的方法两种可选。
    # 建议选择传统方法，深度学习算法所得图像色调偏黄，在后续生锈检测过程可能引起误判
    # ----------------------------
    method_sel = 'classic' #['classic','dl','no_process']
    enhanced_image_path = "./images/enhanced.png"

    if method_sel == 'classic':

        # 根据当前图像的参数反推出图像增强参数
        # 1. Gamma校正参数（亮度调节）
        if original_params["brightness"] < 0.3:  # 过暗
            gamma = 0.5  # 强提亮
        elif original_params["brightness"] > 0.7:  # 过亮
            gamma = 1.6  # 强压暗
        else:  # 正常亮度
            gamma = 1.0  # 基本不调整
        
        # 2. CLAHE参数（对比度调节）
        if original_params["contrast"] < 0.4:  # 低对比度
            clahe_clip = 3.0  # 强增强
            clahe_grid = (8, 8)  # 细粒度分块
        elif original_params["contrast"] > 0.8:  # 高对比度
            clahe_clip = 1.2  # 弱增强
            clahe_grid = (4, 4)  # 粗粒度分块
        else:  # 正常对比度
            clahe_clip = 2.0  # 中等增强
            clahe_grid = (8, 8)
        
        # 3. 双边滤波参数（去噪）
        if original_params["noise_level"] < 0.2:  # 低噪声
            bf_d = 3  # 小卷积核
            bf_sigma = 20  # 弱滤波
        elif original_params["noise_level"] > 0.6:  # 高噪声
            bf_d = 7  # 大卷积核
            bf_sigma = 100  # 强滤波
        else:  # 中噪声
            bf_d = 5  # 中等卷积核
            bf_sigma = 50  # 中等滤波

        # 应用推导出的参数进行图像增强
        # 1. 双边滤波去噪
        denoised = cv2.bilateralFilter(image,d=bf_d,sigmaColor=bf_sigma,sigmaSpace=bf_sigma)
        
        # 2. Gamma校正调节亮度
        img_float = denoised.astype(np.float32) / 255.0 # 转换为float32避免溢出
        gamma_corrected = np.power(img_float, gamma) 
        gamma_corrected = (gamma_corrected * 255).astype(np.uint8)  # 转回uint8
        
        # 3. CLAHE增强对比度（在LAB空间的L通道上操作，避免色彩失真）
        lab = cv2.cvtColor(gamma_corrected, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clahe_clip,tileGridSize=clahe_grid)
        l_enhanced = clahe.apply(l)
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        enhanced_image = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

        cv2.imwrite(enhanced_image_path,enhanced_image)

    elif method_sel == 'dl':
        # 图像预处理，转为tensor格式
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        scale_factor = 12
        data_lowlight = (np.asarray(image)/255.0)
        data_lowlight = torch.from_numpy(data_lowlight).float()
        h=(data_lowlight.shape[0]//scale_factor)*scale_factor
        w=(data_lowlight.shape[1]//scale_factor)*scale_factor
        data_lowlight = data_lowlight[0:h,0:w,:]
        data_lowlight = data_lowlight.permute(2,0,1)
        data_lowlight = data_lowlight.cuda().unsqueeze(0)

        # 应用深度学习方法进行增强
        model_path = './models/enhance.pth'
        enhance_net = enhance_net_nopool(scale_factor).cuda()
        enhance_net.load_state_dict(torch.load(model_path))
        enhanced_image,_ = enhance_net(data_lowlight)

        torchvision.utils.save_image(enhanced_image, enhanced_image_path)

        # 将输出图像转为numpy数组格式
        enhanced_image = enhanced_image.cpu().detach().numpy().squeeze()
        enhanced_image = np.transpose(enhanced_image, (1, 2, 0))
        enhanced_image = (enhanced_image * 255).astype(np.uint8)
        enhanced_image = cv2.cvtColor(enhanced_image, cv2.COLOR_RGB2BGR)

    else:
        enhanced_image = image
        cv2.imwrite(enhanced_image_path,enhanced_image)

    # ----------------------------
    # 评估增强后的图像并整理为指定输出格式
    # ----------------------------
    enhanced_params = get_image_params(enhanced_image)
    result =  {
        "enhanced_image": enhanced_image_path,
        "quality_metrics": enhanced_params,
        "status": "success"
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def roi_extraction(content: str) -> str:
    """
    ROI区域提取工具，从增强后的图像中提取感兴趣区域
    
    Args:
        content: 输入的增强图像数据描述
        
    Returns:
        str: ROI提取结果的JSON字符串
    """

    def draw_detection_res(overall_class_names, target_img, preds):
        colors = Colors()
        for result in preds:
            boxes = result.boxes.xyxy.detach().cpu().numpy() 
            confidences = result.boxes.conf.detach().cpu().numpy() 
            class_ids = result.boxes.cls.detach().cpu().numpy().astype(int)
            class_names = result.names  

        for i in range(len(boxes)):
            box = boxes[i]
            conf = confidences[i]
            cls_id = class_ids[i]
            cls_name = class_names[cls_id]

            if cls_name in overall_class_names:
                overall_cls_id = overall_class_names.index(cls_name)
                
                plot_one_box(
                    box, 
                    target_img,
                    label=f"{cls_name} {conf:.2f}", 
                    color=colors(overall_cls_id), 
                    line_width=3
                )

    def plot_one_box(box, img, label=None, color=None, line_width=3):
        # 转换为整数坐标
        x1, y1, x2, y2 = map(int, box)
        
        # 绘制边框
        cv2.rectangle(img, (x1, y1), (x2, y2), color, line_width)
        
        # 绘制标签
        if label:
            # 计算文本尺寸
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 2
            (text_width, text_height), _ = cv2.getTextSize(label, font, font_scale, line_width)
            
            # 绘制标签背景（半透明填充）
            cv2.rectangle(
                img,
                (x1, y1 - text_height - 5),
                (x1 + text_width, y1),
                color,
                -1  # 填充整个矩形
            )
            
            # 绘制标签文本
            cv2.putText(
                img,
                label,
                (x1, y1 - 5),
                font,
                font_scale,
                (0, 0, 0),
                line_width
            )
        return img

    print("roi_extraction工具被调用")

    # ----------------------------
    # 初始化相关参数和路径
    # ----------------------------
    screw_model_path = "./models/screw_det.pt"
    other_model_path = "./models/other_det.pt"
    class_names = ["chuanganqi", "sidescrew", "screw", "youchuang", "zhouxiang"]
    chinese_class_names = ["传感器", "侧置螺栓", "螺栓头", "油窗", "轴箱"]
    img_size = 640
    device = "cuda" 

    # ----------------------------
    # 加载图像和检测模型
    # ----------------------------
    input_path = json.loads(content)["enhanced_image"]
    image = cv2.imread(input_path)
    screw_model = YOLO(screw_model_path) # 用于检测螺栓头和侧置螺栓
    other_model = YOLO(other_model_path) # 用于检测传感器，油窗，轴箱

    preds = screw_model(
        image,
        imgsz=img_size,
        device=device,
        conf=0.1, 
        iou=0.5
    )
    other_preds = other_model(
        image,
        imgsz=img_size,
        device=device,
        conf=0.1, 
        iou=0.1
    )

    # ----------------------------
    # 在图像中标记检测结果并保存
    # ----------------------------
    detected_image = image.copy()
    draw_detection_res(class_names, detected_image, preds)
    draw_detection_res(class_names, detected_image, other_preds)

    detected_image_path = "./images/detected.png"
    cv2.imwrite(detected_image_path,detected_image)

    # ----------------------------
    # 将检测结果整理为指定输出格式
    # ----------------------------
    result = {
        "original_image": input_path,
        "roi_regions": [],
        "coverage_ratio": 0,
        "status": "success"
    }
    
    # 解析预测结果
    save_roi_imgs = True
    roi_save_path = os.path.join("./images","roi")
    if os.path.exists(roi_save_path):
        os.system('rm -rf '+roi_save_path) 
    os.mkdir(roi_save_path)

    for img_idx, pred in enumerate(preds):
        # 获取图像尺寸（用于后续坐标验证）
        img_height, img_width = pred.orig_shape  # 原始图像的高和宽
        
        # 遍历当前图像中的所有检测框
        for box_idx, box in enumerate(pred.boxes):
            # 提取类别信息（component_type）
            class_id = int(box.cls[0].cpu().numpy())  # 类别ID
            cur_result_names = pred.names
            cls_name = cur_result_names[class_id]
            if cls_name in class_names:
                component_type = chinese_class_names[class_names.index(cls_name)]

                # 提取边界框坐标（YOLO返回的是[xyxy]格式：左上角x, y，右下角x, y）
                xyxy = box.xyxy[0].cpu().numpy().astype(int)  # 转换为整数坐标
                x1, y1, x2, y2 = xyxy  # 左上角(x1,y1)，右下角(x2,y2)
                coordinates = xyxy.tolist()

                # 生成region_id（格式：roi_序号）
                region_id = f"roi_{len(result['roi_regions'])}"  # 累加计数

                # 提取检测置信度
                confidence = box.conf[0].cpu().numpy().item()  # 转换为Python浮点数
                confidence = round(confidence, 2)  # 保留4位小数

                # 保存ROI图像数据
                roi_img_path = os.path.join(roi_save_path,region_id+'.png')
                if save_roi_imgs:
                    roi_img = pred.orig_img[y1:y2, x1:x2]  # 从原始图像中裁剪ROI
                    cv2.imwrite(roi_img_path,roi_img)
                    
                # 构造单个ROI区域的字典
                roi = {
                    "region_id": region_id,
                    "coordinates": coordinates,
                    "image_data": roi_img_path,
                    "component_type": component_type,
                    "confidence": confidence
                }
                
                # 添加到roi_regions列表
                result["roi_regions"].append(roi)
    
    # 计算coverage_ratio (检测区域总面积 / 图像总面积)
    if len(result["roi_regions"]) > 0:
        img_area = preds[0].orig_shape[0] * preds[0].orig_shape[1]
        roi_total_area = sum((x2 - x1) * (y2 - y1) for x1, y1, x2, y2 in [r["coordinates"] for r in result["roi_regions"]])
        result["coverage_ratio"] = float(min(1.0, roi_total_area / img_area))
    
    # 处理无检测结果的情况
    if len(result["roi_regions"]) == 0:
        result["status"] = "no_detections"
    
    return json.dumps(result, ensure_ascii=False, indent=2)


# ==================== 检测分析工具定义 ====================

@tool
def component_segmentation(content: str) -> str:
    """
    组件分割工具，识别和分割轨道部件
    
    Args:
        content: 输入的ROI区域数据描述
        
    Returns:
        str: 组件分割结果的JSON字符串
    """
    print("component_segmentation工具被调用")
    result = {
        "segmented_components": [
            {
                "component_id": "comp_1",
                "class": "轨道",
                "mask": "分割掩码(模拟)",
                "confidence": 0.92,
                "bounding_box": [100, 100, 500, 300]
            },
            {
                "component_id": "comp_2",
                "class": "螺栓",
                "mask": "分割掩码(模拟)",
                "confidence": 0.89,
                "bounding_box": [200, 150, 250, 200]
            }
        ],
        "segmentation_accuracy": 0.91,
        "status": "success"
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def bolt_detection(content: str) -> str:
    """
    螺栓检测工具，定位螺栓等关键部件
    
    Args:
        content: 输入的分割组件数据描述
        
    Returns:
        str: 螺栓检测结果的JSON字符串
    """
    print("bolt_detection工具被调用")
    result = {
        "detected_bolts": [
            {
                "bolt_id": "bolt_1",
                "position": [220, 175],
                "size": 25,
                "orientation": 15.2,
                "confidence": 0.94
            },
            {
                "bolt_id": "bolt_2",
                "position": [280, 180],
                "size": 28,
                "orientation": -3.5,
                "confidence": 0.91
            },
            {
                "bolt_id": "bolt_15",
                "position": [520, 220],
                "size": 26,
                "orientation": 12.5,
                "confidence": 0.92
            },
            {
                "bolt_id": "bolt_22",
                "position": [680, 250],
                "size": 27,
                "orientation": 18.3,
                "confidence": 0.88
            }
        ],
        "detection_confidence": 0.93,
        "total_bolts_detected": 24,
        "status": "success"
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def looseness_analysis(content: str) -> str:
    """
    松动分析工具，评估螺栓健康状态和松动程度
    
    Args:
        content: 输入的螺栓检测数据描述
        
    Returns:
        str: 松动分析结果的JSON字符串
    """
    def find_lines(screw_imgs):
        edge_images = []
        overall_images = []
        for idx, image in enumerate(screw_imgs):
            # 转换为HSV颜色空间
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv[:,:,0], 0, 17)

            # 对Mask进行形态学操作，去除噪声并连接线条
            kernel = np.ones((3, 3), np.uint8)
            mask = cv2.erode(mask, kernel, iterations=1)
            mask = cv2.dilate(mask, kernel, iterations=1)

            # 生成分析过程的可视化图像
            # mask_visual = cv2.cvtColor(255-mask, cv2.COLOR_GRAY2BGR) 
            # overlay = cv2.addWeighted(image, 0.7, mask_visual, 0.3, 0)
            mask_visual = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            overall = np.hstack((image,mask_visual))

            # 骨架提取
            binary = (mask / 255).astype(bool)
            skeleton_bool = skeletonize(binary)
            edges = (skeleton_bool * 255).astype(np.uint8)

            #去除噪声点
            r,c = edges.shape[:2]
            scalar = 0.1
            rbias = int(r*scalar)
            cbias = int(c*scalar)
            edges[0:rbias,:] = 0
            edges[r-rbias:r,:] = 0
            edges[:,0:cbias] = 0
            edges[:,c-cbias:c] = 0

            edge_images.append(edges)
            overall_images.append(overall)

        return edge_images,overall_images

    def get_model(model_type, encoder_name, encoder_weights):
        model_dict = {
            'DeepLabV3Plus': smp.DeepLabV3Plus,
            'Unet': smp.Unet,
            'UnetPlusPlus': smp.UnetPlusPlus,
            'FPN': smp.FPN,
            'PAN': smp.PAN,
            'Linknet': smp.Linknet,
            'PSPNet': smp.PSPNet,
            'MAnet':smp.MAnet
        }
        
        if model_type in model_dict:
            return model_dict[model_type](
                encoder_name=encoder_name,
                encoder_weights=encoder_weights,
                in_channels=3,
                classes=3
            )
        else:
            raise ValueError(f"Model type '{model_type}' not recognized. Available types: {list(model_dict.keys())}")

    print("looseness_analysis工具被调用")

    # ----------------------------
    # 加载图像
    # ----------------------------
    screw_imgs = []
    original_img = cv2.imread(json.loads(content)["original_image"])
    roi_infos = json.loads(content)["roi_regions"]
    for roi_info in roi_infos:
        roi_img_path = roi_info["image_data"]
        roi_img_type = roi_info["component_type"]
        if "螺栓" in roi_img_type:
            if os.path.exists(roi_img_path):
                screw_img = cv2.imread(roi_img_path)
            else:
                x1, y1, x2, y2 = roi_info["coordinates"]
                screw_img = original_img[y1:y2, x1:x2]
            screw_imgs.append(screw_img)

    # ----------------------------
    # 获取螺栓图像中的标识线
    # ----------------------------
    loose_screws = 0
    angel_diff_thres = 30
    looseness_analysis = []
    show_analysis = True
    show_analysis_path = os.path.join("./images","looseness_analysis")
    if os.path.exists(show_analysis_path):
        os.system('rm -rf '+show_analysis_path) 
    os.mkdir(show_analysis_path)

    # ----------------------------
    # 有传统图像处理和基于深度学习的方法两种可选，深度学习方法的鲁棒性更好。
    # ----------------------------
    method_sel = "dl" # ["dl","classic"]

    if method_sel == "dl":
        # 加载模型和初始化配置
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model_type = 'MAnet'
        encoder_name = 'mit_b5'
        encoder_weights = 'imagenet'
        model_path = './models/MAnetmit_b58v2121.pth'
        model = get_model(model_type, encoder_name, encoder_weights).to(device)
        model.load_state_dict(torch.load(model_path, map_location=device))
        model.eval()

        preprocess = transforms.Compose([
            transforms.Resize((128, 128)),
            transforms.ToTensor(),
        ])

        edge_images = []
        overall_images = []
        for idx, image in enumerate(screw_imgs):
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # #debug
            # image_rgb = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
            # image_rgb = cv2.cvtColor(image_rgb, cv2.COLOR_GRAY2RGB)

            image_rgb = Image.fromarray(image_rgb)

            input_tensor = preprocess(image_rgb).unsqueeze(0).to(device)  # 添加批次维度
    
            # 推理
            with torch.no_grad():
                output = model(input_tensor)
                output = torch.argmax(output, dim=1).squeeze(0).cpu().numpy()  # 获取分割结果（每个像素类别）
            output[output == 1] = 0  

            # 保存分割结果
            mask = (output * 255 / output.max()).astype(np.uint8) 
            mask = cv2.resize(mask, (image.shape[1], image.shape[0]))

            # 生成分析过程的可视化图像
            mask_visual = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
            overall = np.hstack((image,mask_visual))

            # 提取骨架
            skeleton = skeletonize(mask)
            edges = (skeleton * 255).astype(np.uint8)

            edge_images.append(edges)
            overall_images.append(overall)
    else:
        edge_images,overall_images = find_lines(screw_imgs)

    for idx, edges in enumerate(edge_images):
        image = screw_imgs[idx]
        overall = overall_images[idx]
        edges_visual = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        overall = np.hstack((overall,edges_visual))

        # 霍夫直线检测
        lines = cv2.HoughLinesP(
            edges, 
            rho=1, 
            theta=np.pi/180, 
            threshold=5,
            minLineLength=10,
            maxLineGap=5
        )

        show_lines = image.copy()
        loose_status = "正常"

        if lines is None:
            loose_status = "未知"
            looseness_analysis.append({
                "screw_id": f"screw_{idx}",
                "orientation_difference": None,
                "looseness_status": loose_status
            })
        else:
            # 计算每条直线的斜率并存储结果
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if x2 - x1 == 0:
                    slope = float('inf')
                else:
                    slope = (y2 - y1) / (x2 - x1)
                angle = math.degrees(math.atan(slope))
                angles.append(angle)

                cv2.line(show_lines, (x1, y1), (x2, y2), (0, 255, 0), 2)

            
            if len(angles) == 1:
                # 若只检测出一根直线，说明标识线是完全对齐的
                looseness_analysis.append({
                    "screw_id": f"screw_{idx}",
                    "orientation_difference":0,
                    "looseness_status": loose_status
                })
            else:
                angle_diff = abs(max(angles)-min(angles))
                angle_diff = min(angle_diff, 180-angle_diff)

                if abs(angle_diff)>angel_diff_thres:
                    loose_status = "松动"
                    loose_screws += 1

                looseness_analysis.append({
                    "screw_id": f"screw_{idx}",
                    "orientation_difference":round(angle_diff, 2),
                    "looseness_status": loose_status
                })

        if show_analysis:
            # 保存分析过程的中间结果，用于展示
            overall = np.hstack((overall,show_lines))
            img_path = os.path.join(show_analysis_path,f"screw_{idx}"+'.png')
            cv2.imwrite(img_path,overall)

            print(f"screw_{idx}"+'  '+loose_status)

    
    loose_ratio = loose_screws / len(screw_imgs) if len(screw_imgs) > 0 else 0.0
    if loose_ratio < 0.1:
        overall_loose_level = "低"
    elif loose_ratio < 0.3:
        overall_loose_level = "中等"
    else: 
        overall_loose_level = "高"

    result = {
        "looseness_analysis": looseness_analysis,
        "summary": {
            "normal_screws": len(screw_imgs) - loose_screws,
            "loose_screws": loose_screws,
            "overall_risk": overall_loose_level
        },
        "status": "success"
    }

    return json.dumps(result, ensure_ascii=False, indent=2)

@tool
def rust_analysis(content: str) -> str:
    """
    螺栓生锈情况分析工具
    
    Args:
        content: 输入的螺栓检测数据描述
        
    Returns:
        str: 生锈分析结果的JSON字符串
    """
    print("rust_analysis工具被调用")

    # ----------------------------
    # 初始化相关参数
    # ----------------------------
    rust_det_model_path = "./models/rust_det_yolo.pt"
    img_size = 128
    device = "cuda"

    # ----------------------------
    # 加载图像和分类模型
    # ----------------------------
    rust_model = YOLO(rust_det_model_path) # 仅用于检测螺栓头和侧置螺栓是否生锈

    screw_imgs = []
    original_img = cv2.imread(json.loads(content)["original_image"])
    roi_infos = json.loads(content)["roi_regions"]
    for roi_info in roi_infos:
        roi_img_path = roi_info["image_data"]
        roi_img_type = roi_info["component_type"]
        if "螺栓" in roi_img_type:
            if os.path.exists(roi_img_path):
                screw_img = cv2.imread(roi_img_path)
            else:
                x1, y1, x2, y2 = roi_info["coordinates"]
                screw_img = original_img[y1:y2, x1:x2]
            screw_imgs.append(screw_img)
    
    # ----------------------------
    # 对每张螺栓的图像进行生锈检测
    # ----------------------------
    preds = rust_model(
        screw_imgs,
        imgsz=img_size,
        device=device
    )

    # ----------------------------
    # 将检测结果整理为指定输出格式
    # ----------------------------
    result = {
        "rust_analysis": [],
        "summary": None,
        "status": "success"
    }
    rusted_screws = 0
    rust_thres = 0.95
    for idx, pred in enumerate(preds):

        rust_status = "正常"
        if pred.probs.data[1]>rust_thres:
            rust_status = "生锈"
            rusted_screws += 1

        confidence = pred.probs.top1conf.item()

        result["rust_analysis"].append({
            "screw_id": f"screw_{idx}",
            "rust_status": rust_status,
            "confidence": round(confidence, 2)
        })

    rust_ratio = rusted_screws / len(screw_imgs) if len(screw_imgs) > 0 else 0.0
    if rust_ratio < 0.1:
        overall_rust_level = "低"
    elif rust_ratio < 0.3:
        overall_rust_level = "中等"
    else: 
        overall_rust_level = "高"

    result["summary"]={
        "regular_screws": len(screw_imgs) - rusted_screws,
        "rusted_screws": rusted_screws,
        "overall_rust_level": overall_rust_level
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


# ==================== 结果验证工具定义 ====================

@tool
def confidence_calculation(extraction_content: str, looseness_content: str, rust_content: str) -> str:
    """
    置信度计算工具，基于松动分析和锈蚀分析的结果字符串计算整体置信度
    
    Args:
        looseness_content: 松动分析结果
        rust_content: 锈蚀分析结果
        
    Returns:
        str: 置信度计算结果的JSON字符串
    """
    print("confidence_calculation工具被调用")
    
    try:
        # 解析输入的JSON字符串为字典
        ext_data: Dict = json.loads(extraction_content)
        looseness_data: Dict = json.loads(looseness_content)
        rust_data: Dict = json.loads(rust_content)
    except json.JSONDecodeError as e:
        # 处理JSON解析错误
        return json.dumps({
            "confidence_scores": {},
            "validation_passed": False,
            "status": "failed",
            "error": f"JSON解析错误: {str(e)}"
        }, ensure_ascii=False, indent=2)

    # 1.获取检测结果置信度
    ext_res = ext_data.get('roi_regions', [])
    ext_confidences = [item.get('confidence', 0.0) for item in ext_res]
    ext_avg_confidence = round(sum(ext_confidences) / len(ext_confidences if ext_confidences else 0.0),2)

    # 2. 计算锈蚀分析组件置信度（取所有螺栓置信度的平均值）
    rust_analysis = rust_data.get('rust_analysis', [])
    rust_confidences = [item.get('confidence', 0.0) for item in rust_analysis]
    rust_avg_confidence = round(sum(rust_confidences) / len(rust_confidences) if rust_confidences else 0.0,2)

    # 3. 计算松动分析组件置信度（正常螺栓占比）
    looseness_analysis = looseness_data.get('looseness_analysis', [])
    total_screws = len(looseness_analysis)
    normal_screws = looseness_data.get('summary', {}).get('normal_screws', 0)
    looseness_confidence = round(normal_screws / total_screws if total_screws > 0 else 0.0,2)

    # 4. 计算整体置信度（加权平均）
    overall_confidence = round(0.4 * ext_avg_confidence + 0.3 * rust_avg_confidence + 0.3 * looseness_confidence, 2)

    # 5. 综合风险评估（基于两者的风险等级）
    risk_mapping = {
        ('低', '低'): '低',
        ('低', '中'): '中',
        ('低', '高'): '高',
        ('中', '低'): '中',
        ('中', '中'): '中',
        ('中', '高'): '高',
        ('高', '低'): '高',
        ('高', '中'): '高',
        ('高', '高'): '高'
    }
    looseness_risk = looseness_data.get('summary', {}).get('overall_risk', '中')
    rust_risk = rust_data.get('summary', {}).get('overall_rust_level', '中')
    overall_risk = risk_mapping.get((looseness_risk, rust_risk), '中')

    # 6. 验证状态是否成功
    validation_passed = (
        looseness_data.get('status') == 'success' and
        rust_data.get('status') == 'success'
    )

    # 7. 构建结果
    result = {
        "confidence_scores": {
            "overall_confidence": overall_confidence,
            "component_confidence": {
                "identification":ext_avg_confidence,
                "looseness_analysis": looseness_confidence,
                "rust_analysis": rust_avg_confidence
            },
            "risk_assessment": overall_risk
        },
        "validation_passed": validation_passed,
        "status": "success" if validation_passed else "failed"
    }

    # print(result)
    return json.dumps(result, ensure_ascii=False, indent=2)


@tool
def cross_validation(content: str) -> str:
    """
    交叉验证工具，验证分析结果的可靠性
    
    Args:
        content: 输入的主要分析结果描述
        
    Returns:
        str: 交叉验证结果的JSON字符串
    """
    print("cross_validation工具被调用")
    result = {
        "validation_results": {
            "agreement_score": 0.87,
            "inconsistent_findings": [
                {
                    "component": "bolt_22",
                    "primary_result": "松动",
                    "secondary_result": "正常",
                    "resolution": "采用主要结果"
                }
            ],
            "final_validation": "passed"
        },
        "status": "success"
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def create_data_analysis_graph():
    """
    创建数据分析与洞察子图，包含3个Agent节点和对应的工具节点
    
    Returns:
        编译后的langgraph子图
    """
    base_url = os.getenv('OPENAI_BASE_URL')
    api_key = "123"

    if not api_key:
        raise ValueError("请设置OPENAI_API_KEY环境变量: data_analysis_graph.py")

    # 创建LLM实例
    llm = ChatOpenAI(
        base_url=base_url,
        api_key=api_key,
        temperature=0.7,
        max_tokens=2000
    )

    # 创建状态图
    graph = StateGraph(State)
    
    # 创建3个Agent节点
    data_preprocessing_agent = create_react_agent(
        llm,
        [image_enhancement, roi_extraction],
        prompt="""你是数据预处理专家，负责准备高质量的分析数据。
        
        任务：
        1. 从指定位置获取原始数据
        2. 应用数据增强和预处理技术（调用image_enhancement工具）
        3. 提取感兴趣区域ROI（调用roi_extraction工具）
        4. 确保数据质量符合后续分析要求
        
        每次分析都需要依次调用image_enhancement和roi_extraction工具，不能仅凭经验回答。
        你的回答应以"数据预处理："开头。"""
    )
    
    # detection_analysis_agent = create_react_agent(
    #     llm,
    #     [component_segmentation, bolt_detection, looseness_analysis],
    #     prompt="""你是检测分析专家，负责执行具体的缺陷检测和分析算法。
        
    #     任务：
    #     1. 组件分割：识别和分割轨道部件（调用component_segmentation工具）
    #     2. 目标检测：定位螺栓等关键部件（调用bolt_detection工具）
    #     3. 状态分析：评估部件健康状态（调用looseness_analysis工具）
        
    #     每次分析都需要依次调用这3个工具，不能仅凭经验回答。
    #     你的回答应以"检测分析："开头。"""
    # )
    detection_analysis_agent = create_react_agent(
        llm,
        [looseness_analysis, rust_analysis],
        prompt="""你是检测分析专家，负责执行具体的缺陷检测和分析算法。
        
        任务：
        1.评估螺栓松动状态（调用looseness_analysis工具）
        2.评估螺栓腐蚀状态（调用rust_analysis工具）
        
        每次分析都需要依次调用这2个工具，不能仅凭经验回答。
        你的回答应以"检测分析："开头。"""
    )
    
    result_validation_agent = create_react_agent(
        llm,
        [confidence_calculation, cross_validation],
        prompt="""你是结果验证专家，负责整合分析结果并进行质量验证。
        
        任务：
        1. 计算整体置信度（调用confidence_calculation工具）
        2. 交叉验证结果可靠性（调用cross_validation工具）
        3. 生成结构化报告
        4. 质量最终检查
        
        每次分析都需要依次调用confidence_calculation和cross_validation工具，不能仅凭经验回答。
        你的回答应以"结果验证："开头，并生成完整的巡检报告JSON。"""
    )
    
    # 创建工具节点
    data_preprocessing_tools = ToolNode([image_enhancement, roi_extraction])
    # detection_analysis_tools = ToolNode([component_segmentation, bolt_detection, looseness_analysis])
    detection_analysis_tools = ToolNode([looseness_analysis,rust_analysis])
    result_validation_tools = ToolNode([confidence_calculation, cross_validation])
    
    # 创建最终总结节点
    final_summary_agent = common_llm(
        prompt="""你是数据分析总结专家，负责整合数据预处理、检测分析和结果验证的所有结果。
        
        你需要：
        1. 综合3个模块的分析结果
        2. 生成完整的巡检报告，包含检测ID、位置、时间、结果详情和质量指标
        3. 确保不遗漏任何关键信息
        
        最终输出格式应为：
        {
          "inspection_id": "...",
          "location": "3号线路K25+300",
          "inspection_time": "...",
          "results": {
            "total_bolts_inspected": 24,
            "loose_bolts": [...],
            "overall_risk_assessment": "...",
            "recommendations": [...]
          },
          "quality_metrics": {
            "processing_time": "...",
            "overall_confidence": ...,
            "coverage": "..."
          }
        }
        
        你的回答应以"数据分析总结："开头。"""
    )
    
    # 添加Agent节点和工具节点
    graph.add_node("数据预处理Agent", data_preprocessing_agent,
                   metadata={"description": "数据预处理专家，负责图像增强和ROI提取"})
    graph.add_node("数据预处理工具", data_preprocessing_tools,
                   metadata={"description": "执行图像增强和ROI提取工具"})
    
    graph.add_node("检测分析Agent", detection_analysis_agent,
                   metadata={"description": "检测分析专家，负责组件分割、螺栓检测和松动分析"})
    graph.add_node("检测分析工具", detection_analysis_tools,
                   metadata={"description": "执行组件分割、螺栓检测和松动分析工具"})
    
    graph.add_node("结果验证Agent", result_validation_agent,
                   metadata={"description": "结果验证专家，负责置信度计算和交叉验证"})
    graph.add_node("结果验证工具", result_validation_tools,
                   metadata={"description": "执行置信度计算和交叉验证工具"})
    
    graph.add_node("数据分析总结节点", final_summary_agent,
                   metadata={"description": "整合所有分析结果，生成完整的巡检报告"})
    
    # 添加边：线性流程
    graph.add_edge(START, "数据预处理Agent")
    graph.add_edge("数据预处理Agent", "数据预处理工具")
    graph.add_edge("数据预处理工具", "检测分析Agent")
    graph.add_edge("检测分析Agent", "检测分析工具")
    graph.add_edge("检测分析工具", "结果验证Agent")
    graph.add_edge("结果验证Agent", "结果验证工具")
    graph.add_edge("结果验证工具", "数据分析总结节点")
    graph.add_edge("数据分析总结节点", END)
    
    return graph.compile()


# 创建全局图实例
data_analysis_subgraph = create_data_analysis_graph()


# enhance_res = image_enhancement("")
# det_res = roi_extraction(enhance_res)
# rust_det_res = rust_analysis(det_res)
# loose_det_res = looseness_analysis(det_res)
# res = confidence_calculation(det_res, loose_det_res, rust_det_res)