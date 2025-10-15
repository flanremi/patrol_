#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

import requests
from langchain_core.tools import tool
from DB_helper import EmbeddingDBHelper


# 初始化数据库助手
db_helper = EmbeddingDBHelper(embedding_path="memory_embedding")


@tool
def search_fault(img_path: str, object_name: str) -> str:
    """
    查询制定路径的图片是否有故障
    
    Args:
        img_path: 希望查询故障的图像路径
        object_name: 监测目标类型 （映射：瓶子->bottle）
    Returns:
        故障检索报告
    """

    with open(img_path, "rb") as f:
        response = requests.post("http://10.10.0.237:8000/detect",
                                 files={"file": f},
                                 data={"object_name": object_name, "threshold": 0.15})
        json_resp = response.json()
        json_resp.pop("qwen_judgment")
        return json.dumps(json_resp)

