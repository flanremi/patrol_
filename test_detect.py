import requests

# 异常检测
with open("Fault_img/004.png", "rb") as f:
    response = requests.post("http://10.10.0.237:8000/detect",
                           files={"file": f},
                           data={"object_name": "bottle", "threshold": 0.15})
    result = response.json()
    print(f"异常分数: {result['anomaly_score']}")
    print(f"是否异常: {result['is_anomaly']}")
    print(f"置信度: {result['confidence']}")