# Autodidact AI Core: Optimization and Scaling Roadmap

## 1. Introduction

This document provides a detailed, phased roadmap for evolving the `autodidact-ai-core` project from its current state into a robust, scalable, and production-grade AI system. The goal is to systematically enhance the application's architecture, data processing capabilities, and machine learning models to build a high-quality, specialized knowledge base.

This plan is designed to be actionable by either an AI agent or a human engineer, with specific technologies and implementation steps for each phase.

---

## 2. Executive Summary of Analysis

The `autodidact-ai-core` project has a solid foundation with a Python-based, multi-agent architecture for ingesting YouTube content into a ChromaDB vector store. To elevate this to a professional, production-level system, a dedicated team would focus on the following key areas:

1.  **Data Ingestion Pipeline:** Decoupling services for scalability and resilience, diversifying data sources, and implementing sophisticated, multi-dimensional quality scoring with a human-in-the-loop system.
2.  **AI/ML & Vector DB Strategy:** Migrating to a production-grade vector database, implementing advanced hybrid search and re-ranking, and fine-tuning custom embedding and generator models for domain-specific accuracy.
3.  **System Architecture & MLOps:** Transitioning from `docker-compose` to a cloud-native architecture (Kubernetes), establishing automated CI/CD pipelines, managing infrastructure as code (IaC), and implementing comprehensive system and model monitoring.

---

## 3. Detailed Implementation Plan

This plan is divided into three sequential phases, each building upon the last.

### Phase 1: Foundational Scaling

**Goal:** Decouple the system for resilience, enable horizontal scaling, and automate testing and deployment.

#### **Task 1.1: Decouple Components with a Message Queue**

*   **Objective:** Replace the current synchronous orchestration with an asynchronous, message-based system. This isolates components and allows them to scale independently.
*   **Recommended Technology:** **RabbitMQ**. It is a mature, feature-rich message broker ideal for building resilient data processing pipelines.
*   **Instructions for Implementation:**
    1.  **Update `docker-compose.yml`:** Add a `rabbitmq` service using the official Docker image (`rabbitmq:3-management`). Expose the management interface port `15672`.
    2.  **Update `requirements.txt`:** Add the Python client for RabbitMQ: `pika`.
    3.  **Refactor the Orchestrator (`indexing_orchestrator.py`):**
        *   Modify the orchestrator to become a "producer." Instead of calling processing logic directly, its role is to publish initial tasks (e.g., a JSON message with a video URL and metadata) to a RabbitMQ queue (e.g., `tasks.video.new`).
    4.  **Create Independent Worker Services:**
        *   Create a new directory `src/workers/`.
        *   Implement individual Python scripts for each stage of the pipeline (e.g., `transcription_worker.py`, `quality_assessment_worker.py`, `question_generation_worker.py`, `embedding_worker.py`).
        *   Each worker will:
            *   Connect to RabbitMQ.
            *   Consume messages from an input queue (e.g., `transcription_worker` consumes from `tasks.video.new`).
            *   Perform its specific task (e.g., download and transcribe).
            *   Publish the result to an output queue for the next stage (e.g., `tasks.video.transcribed`).
            *   Acknowledge the message to remove it from the input queue.
    5.  **Update `docker-compose.yml`:** Add new services for each worker, which run the corresponding worker scripts. Use `restart: always` to ensure they are resilient.

#### **Task 1.2: Migrate to Kubernetes for Production Deployment**

*   **Objective:** Move from a local `docker-compose` setup to a scalable, production-ready container orchestration platform.
*   **Recommended Technology:** **Kubernetes (K8s)**. Use **Minikube** for local development and a managed service like **Amazon EKS**, **Google GKE**, or **Azure AKS** for production.
*   **Instructions for Implementation:**
    1.  **Create Kubernetes Manifests:**
        *   Create a new top-level directory named `k8s/`.
        *   For each service in your architecture (API server, RabbitMQ, Redis, and each worker), create a Kubernetes manifest file.
            *   **`Deployment`:** Define the pod specification, including the Docker image, desired number of replicas, environment variables, and resource requests/limits. This allows for easy scaling (e.g., `kubectl scale deployment transcription-worker --replicas=10`).
            *   **`Service`:** Define how to expose your deployments. Use `ClusterIP` for internal services (like RabbitMQ) and `LoadBalancer` or `Ingress` for public-facing services (like the API).
    2.  **Manage Configuration and Secrets:**
        *   Convert `proxy_config.json` and other configurations into a Kubernetes `ConfigMap`. Mount this `ConfigMap` as a volume into your pods.
        *   Store sensitive data like API keys and database credentials in Kubernetes `Secrets`, not in configuration files or Docker images.
    3.  **Documentation:** Create a `k8s/README.md` that explains how to set up the Kubernetes cluster and apply the manifests using `kubectl apply -f k8s/`.

#### **Task 1.3: Implement CI/CD for Automation**

*   **Objective:** Automate testing and deployment to ensure code changes are validated and deployed reliably.
*   **Recommended Technology:** **GitHub Actions**.
*   **Instructions for Implementation:**
    1.  **Create Workflow Directory:** Create `.github/workflows/`.
    2.  **Create `ci.yml` Workflow:**
        *   **Trigger:** Configure the workflow to run on `push` events to the `main` branch and on `pull_request` events.
        *   **Jobs:**
            1.  **`lint-and-test`:**
                *   Set up a Python environment.
                *   Install dependencies from `requirements.txt`.
                *   Run a linter like `flake8` or `ruff` to enforce code style.
                *   Run all unit and integration tests using `pytest`.
            2.  **`build-and-push-docker`:**
                *   This job should depend on the success of `lint-and-test`.
                *   Log in to a Docker registry (e.g., Docker Hub, GitHub Container Registry, ECR).
                *   Build, tag, and push the Docker images for your application services. Tag images with the Git commit SHA for versioning.
    3.  **Create `cd.yml` Workflow (Continuous Deployment):**
        *   **Trigger:** Configure this to run only on pushes to the `main` branch, after the `ci.yml` workflow succeeds.
        *   **Jobs:**
            1.  **`deploy-to-k8s`:**
                *   Configure access to your cloud provider and Kubernetes cluster.
                *   Use `kubectl` to apply the manifests from the `k8s/` directory. You may need to update the image tags in your `Deployment` manifests to the newly pushed version (a tool like `kustomize` is excellent for this).

---

### Phase 2: AI/ML and Vector DB Optimization

**Goal:** Enhance the intelligence and accuracy of the core ML system.

#### **Task 2.1: Migrate to a Production-Grade Vector Database**

*   **Objective:** Replace the local ChromaDB instance with a managed, scalable, and more performant vector database.
*   **Recommended Technology:** **Pinecone**, **Weaviate**, or **Zilliz Cloud**.
*   **Instructions for Implementation:**
    1.  **Evaluation:** Sign up for free tiers and run benchmark tests with your own data to evaluate latency and retrieval accuracy for each option.
    2.  **Abstract Database Logic:** Create a generic `VectorStore` interface in your code (`src/db_utils/vector_store.py`) that defines methods like `upsert`, `query`, and `delete`.
    3.  **Create New Implementation:** Write a new class (e.g., `PineconeVectorStore`) that implements this interface using the specific client library for your chosen database.
    4.  **Update Configuration:** Control which vector store implementation is used via an environment variable, allowing you to switch between ChromaDB (for local testing) and the production database.
    5.  **Data Migration:** Write a one-time script to read all data from your existing ChromaDB and upsert it into the new production vector database.

#### **Task 2.2: Implement Advanced Retrieval Strategies**

*   **Objective:** Improve search relevance by moving beyond simple vector similarity.
*   **Recommended Technology:** Your chosen vector database's features for **hybrid search** and a lightweight **cross-encoder model** for re-ranking.
*   **Instructions for Implementation:**
    1.  **Enable Hybrid Search:**
        *   When upserting data, store both the vector embedding and the raw text in the vector database.
        *   Modify your query logic to use the database's hybrid search feature. This typically involves providing both a query vector and the query text, along with a weighting parameter (alpha) to balance between semantic and keyword results.
    2.  **Implement a Re-ranking Layer:**
        *   In your retrieval pipeline, after getting the initial results (e.g., top 50) from hybrid search, pass them to a re-ranking model.
        *   Use a lightweight cross-encoder model (e.g., from the `sentence-transformers` library). A cross-encoder takes the query and a candidate document as a pair and outputs a relevance score.
        *   Sort the initial results by this new relevance score to get the final, re-ranked list. This significantly improves the quality of the top results.

---

### Phase 3: Maturity and Intelligence

**Goal:** Achieve state-of-the-art performance through custom models and establish a continuous improvement loop.

#### **Task 3.1: Fine-Tune Custom Embedding and Generator Models**

*   **Objective:** Train models that understand the specific nuances and terminology of your target domain, leading to superior performance.
*   **Recommended Technology:** **Hugging Face Transformers**, **PyTorch** or **TensorFlow**, and an experiment tracking tool like **MLflow** or **Weights & Biases**.
*   **Instructions for Implementation:**
    1.  **Data Collection:** Build a high-quality dataset for fine-tuning. This can consist of `(query, relevant_passage)` pairs derived from your generated question-answer data.
    2.  **Embedding Model Fine-Tuning:**
        *   Choose a strong open-source embedding model (e.g., `bge-large-en-v1.5`).
        *   Use a contrastive learning approach to train the model to produce similar vectors for relevant pairs and dissimilar vectors for irrelevant pairs. The `sentence-transformers` library has excellent utilities for this.
    3.  **Generator Model Fine-Tuning:**
        *   Choose a strong open-source instruction-tuned model (e.g., `Llama-3-8B-Instruct` or `Mistral-7B-Instruct`).
        *   Format your question-answer pairs into a conversational or instruction-following format.
        *   Fine-tune the model on this dataset. This will teach it to answer questions more accurately and in the desired style.
    4.  **Experiment Tracking:** Use MLflow to log experiments, including model parameters, datasets, and performance metrics. This is crucial for reproducibility.
    5.  **Model Registry:** Store your fine-tuned models in a model registry (MLflow provides one) for versioning and easy deployment.

#### **Task 3.2: Implement a Human-in-the-Loop (HITL) System**

*   **Objective:** Create a feedback loop where human experts can review, correct, and approve AI-generated data, which is then used to continuously improve the AI models.
*   **Recommended Technology:** A simple web framework like **Streamlit** or **FastAPI + React** for the UI, and a backend to store the feedback.
*   **Instructions for Implementation:**
    1.  **Build a Review UI:** Create a simple web application that:
        *   Displays low-confidence outputs from your pipeline (e.g., generated questions with low quality scores, or user queries with poor search results).
        *   Allows a human expert to edit, approve, or reject the data.
    2.  **Store Feedback:** Save this feedback to a database. This feedback becomes a high-quality, curated dataset.
    3.  **Automate Re-training:** Create a scheduled job (e.g., a weekly GitHub Actions workflow) that automatically uses this new, curated dataset to re-run the fine-tuning process from Task 3.1, producing improved versions of your models.
    4.  **Deploy Updated Models:** Once a new model shows improved performance on a validation set, deploy it to production.

#### **Task 3.3: Implement Comprehensive ML Monitoring**

*   **Objective:** Proactively monitor the performance of your models in production to detect issues like data drift or performance degradation.
*   **Recommended Technology:** **Prometheus** and **Grafana** for system metrics, and specialized ML monitoring tools like **Arize**, **WhyLabs**, or open-source alternatives like **Evidently AI**.
*   **Instructions for Implementation:**
    1.  **Log Production Data:** Log all inputs (queries) and outputs (retrieved documents, generated answers) from your production system.
    2.  **Integrate Monitoring Tools:**
        *   Feed these logs into an ML monitoring tool.
        *   Define baseline statistics on your training/validation data.
        *   Set up monitors to detect **data drift** (when the statistical properties of production queries change significantly from the training data) and **concept drift**.
        *   Create alerts that notify the team when drift is detected or when model performance metrics (like user satisfaction, if measured) drop, indicating that a re-training cycle is needed.
