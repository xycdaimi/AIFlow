"""Model Inference - 模型推理调度器"""

import importlib.util
from typing import Dict, Any, Callable
from datetime import datetime, timezone
from core.protocols import TaskStatus
from pathlib import Path


# 推理函数注册表（哈希桶）
# key: task_type, value: 推理函数
INFERENCE_REGISTRY: Dict[str, Callable] = {}


def register_inference_function(task_type: str):
    """
    装饰器：注册推理函数到哈希桶

    Args:
        task_type: 任务类型（例如 "text-generation", "image-generation"）

    Example:
        @register_inference_function("text-generation")
        def text_generation_inference(task_id, task_type, model_spec, payload, inference_params):
            # 调用模型 API
            return {"output": "result"}
    """
    def decorator(func: Callable):
        INFERENCE_REGISTRY[task_type] = func
        print(f"Registered inference function for task_type: {task_type}")
        return func
    return decorator


def load_model_services():
    """
    从 configs/model_services/ 目录加载所有模型服务接口文件
    自动注册所有使用 @register_inference_function 装饰的函数
    """
    # 获取 configs/model_services/ 目录路径
    project_root = Path(__file__).parent.parent.parent
    model_services_dir = project_root / "configs" / "model_services"

    if not model_services_dir.exists():
        print(f"Warning: Model services directory not found: {model_services_dir}")
        return

    # 遍历目录中的所有 .py 文件
    for file_path in model_services_dir.glob("*.py"):
        if file_path.name.startswith("_"):
            continue  # 跳过 __init__.py 等文件

        try:
            # 动态导入模块
            module_name = f"configs.model_services.{file_path.stem}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            print(f"Loaded model service module: {file_path.name}")
        except Exception as e:
            print(f"Error loading model service {file_path.name}: {e}")


def infer(task_id: str, task_type: str, model_spec: Dict[str, Any],
          payload: Dict[str, Any], inference_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    推理调度函数 - 根据 task_type 调用对应的推理函数

    Args:
        task_id: 任务 ID
        task_type: 任务类型
        model_spec: 模型规格配置
        payload: 推理输入数据
        inference_params: 推理参数

    Returns:
        推理结果字典，包含以下字段：
        - task_id: 任务 ID
        - status: "SUCCESS" 或 "FAILED"
        - result: 推理结果（包含 output 字段）
        - error: 错误信息（仅在失败时）
    """
    # 检查是否有对应的推理函数
    if task_type not in INFERENCE_REGISTRY:
        return {
            "task_id": task_id,
            "status": TaskStatus.FAILED,
            "error": f"No inference function registered for task_type: {task_type}. "
                    f"Available types: {list(INFERENCE_REGISTRY.keys())}"
        }

    try:
        # 调用对应的推理函数
        inference_func = INFERENCE_REGISTRY[task_type]
        output = inference_func(model_spec, payload, inference_params)

        # 返回成功结果
        return {
            "task_id": task_id,
            "status": TaskStatus.SUCCESS,
            "result": {
                "output": output,
                "model": model_spec.get("name"),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }

    except Exception as e:
        # 返回失败结果
        return {
            "task_id": task_id,
            "status": TaskStatus.FAILED,
            "error": f"Inference failed: {str(e)}"
        }


# 在模块加载时自动加载所有模型服务
load_model_services()


def get_registered_task_types() -> list:
    """获取所有已注册的任务类型"""
    return list(INFERENCE_REGISTRY.keys())
