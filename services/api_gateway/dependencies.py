#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: xycdaimi
@Email: xycdaimi@gmail.com
@Date: 2025-11-20
@Description: Shared dependencies for API Gateway
"""

from core.utils import RedisClient, RabbitMQClient
from core.storage.minio_client import MinioStore

# Global clients
redis_client = RedisClient()
rabbitmq_client = RabbitMQClient()
minio_store = MinioStore()