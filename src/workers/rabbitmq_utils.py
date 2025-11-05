"""
RabbitMQ connection utilities for workers.
Provides shared configuration and connection management.
"""
import os
import pika
from typing import Optional

# RabbitMQ configuration from environment variables
RABBITMQ_HOST = os.getenv('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.getenv('RABBITMQ_PORT', '5672'))
RABBITMQ_USER = os.getenv('RABBITMQ_USER', 'autodidact')
RABBITMQ_PASSWORD = os.getenv('RABBITMQ_PASSWORD', 'rabbitmq_password')

# Queue names
QUEUE_VIDEO_NEW = 'tasks.video.new'
QUEUE_VIDEO_TRANSCRIBED = 'tasks.video.transcribed'
QUEUE_VIDEO_VALIDATED = 'tasks.video.validated'
QUEUE_VIDEO_INGESTED = 'tasks.video.ingested'


def get_rabbitmq_connection() -> pika.BlockingConnection:
    """
    Establishes a connection to RabbitMQ.
    
    Returns:
        pika.BlockingConnection: Active connection to RabbitMQ
    """
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )
    return pika.BlockingConnection(parameters)


def declare_queue(channel: pika.channel.Channel, queue_name: str, durable: bool = True) -> None:
    """
    Declares a queue if it doesn't exist.
    
    Args:
        channel: RabbitMQ channel
        queue_name: Name of the queue to declare
        durable: Whether the queue should survive broker restarts
    """
    channel.queue_declare(
        queue=queue_name,
        durable=durable,
        arguments={
            'x-message-ttl': 86400000,  # 24 hours in milliseconds
            'x-max-length': 10000,  # Max 10k messages in queue
        }
    )
    print(f"✅ Queue '{queue_name}' declared.")


def setup_all_queues(channel: pika.channel.Channel) -> None:
    """
    Declares all queues used in the pipeline.
    
    Args:
        channel: RabbitMQ channel
    """
    queues = [
        QUEUE_VIDEO_NEW,
        QUEUE_VIDEO_TRANSCRIBED,
        QUEUE_VIDEO_VALIDATED,
        QUEUE_VIDEO_INGESTED,
    ]
    for queue in queues:
        declare_queue(channel, queue)
