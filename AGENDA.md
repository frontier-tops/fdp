# Programme Agenda

**Faculty Development Programme — HPE Generative AI on Private Cloud AI**
*From Foundations to Agentic AI and Physical AI*

CHRIST (Deemed to be University) · Centre for AI Excellence
Delivered by **Frontier Business Systems Pvt. Ltd.**

| | |
|---|---|
| **Duration** | 3 days · 14 sessions · 16 hands-on lab blocks |
| **Format** | Concept-first, then lab — every theory block is followed immediately by hands-on practice |
| **Audience** | Faculty in Computer Science, AI and Data Science; STEM and non-STEM use cases |
| **Platform** | HPE Private Cloud AI developer system with NVIDIA GPUs, Kubeflow notebooks and a shared model-inference service |
| **Daily timing** | 09:30 – 17:00, with morning and afternoon breaks and a one-hour lunch |

## What you will be able to do by Day 3

- Operate a private cloud AI platform: launch GPU notebooks, inspect GPU resources and manage workloads
- Compare open-source language models and apply prompt-engineering techniques with confidence
- Design and build Retrieval-Augmented Generation (RAG) systems over institutional documents
- Deploy inference services and reason about concurrency, latency and throughput
- Build single- and multi-agent workflows, including a Text-to-SQL agent over a real dataset
- Apply evaluation, guardrails and governance to academic AI systems
- Build end-to-end data engineering and machine learning pipelines, including AutoML
- Translate all of the above into coursework, capstone projects and research initiatives

## Before you arrive

- Bring a **laptop with a modern browser** — all labs run in the browser, nothing is installed locally
- **VPN access and lab credentials** will be issued separately by the facilitation team
- For the function-calling lab, create a **free personal API key** at [aistudio.google.com](https://aistudio.google.com) in advance
- No prior platform experience is assumed; familiarity with Python helps but is not required for most labs

---

## Day 1 — Foundations of GenAI, the Platform, and RAG

*Day 1 establishes the platform and the most important enterprise GenAI architecture — retrieval-augmented generation. You finish the day having built a working RAG application over real documents.*

| Time | Session | What happens |
|---|---|---|
| 09:00 – 09:30 | **Registration & Welcome** | Objectives for the three days, platform tour, how theory pairs with labs |
| 09:30 – 10:30 | **S1 · Foundations of GenAI & the Platform** | *Theory:* from traditional ML to GenAI; LLM/transformer intuition; inference vs fine-tuning vs retrieval. *Lab 1:* launch Kubeflow, create a GPU-enabled Jupyter workspace, validate readiness |
| 10:30 – 11:30 | **S2 · Platform Architecture & GPU Resources** | *Theory:* logical architecture; GPU abstraction and isolation. *Lab 2:* inspect GPU configuration, run a baseline GPU workload |
| 11:30 – 11:45 | *Tea / Coffee* | |
| 11:45 – 12:45 | **S3 · Prompting & Model Comparison** | *Theory:* prompt structure; tokens, temperature, model size; latency in shared systems. *Lab 3:* compare LLaMA 3.1 8B, Mistral 7B and Phi-3.5. *Lab 7:* zero-shot, few-shot and chain-of-thought prompting |
| 12:45 – 13:45 | *Lunch* | |
| 13:45 – 15:15 | **S4 · RAG Data Foundations** *(double session)* | *Theory:* why RAG dominates enterprise GenAI; embeddings, vector databases, chunking. *Lab 4A:* embed documents into a vector store. *Lab 4B:* chunking strategies and retrieval accuracy |
| 15:15 – 15:30 | *Tea / Coffee* | |
| 15:30 – 17:00 | **S5 · End-to-End RAG Application** | *Theory:* connecting retrievers to LLMs; reducing hallucination. *Lab 5:* build and tune a complete RAG application |
| 17:00 – 17:15 | **Day 1 Wrap-up & Q&A** | |

**Day 1 outcome:** you can operate the platform, run foundational GenAI experiments, and design, build and teach RAG systems.

---

## Day 2 — Enterprise AI, Inference Services, and Agentic AI

*Day 2 moves from experimentation to production patterns: packaged inference services, then agents that use tools, retrieve knowledge and collaborate with one another.*

| Time | Session | What happens |
|---|---|---|
| 09:15 – 09:30 | *Day 1 recap* | |
| 09:30 – 10:30 | **S6 · Enterprise AI Platform & Reusable Workflows** | *Theory:* NVIDIA AI Enterprise; GPU operators; lifecycle management. *Lab 6:* convert a notebook experiment into a reusable workflow with repeatable runs |
| 10:30 – 11:30 | **S7 · Inference Microservices & Concurrency** | *Theory:* NVIDIA NIM microservices; endpoints; notebook vs service inference. *Lab 7:* issue concurrent requests; watch GPU utilisation, latency, throughput |
| 11:30 – 11:45 | *Tea / Coffee* | |
| 11:45 – 12:45 | **S8 · Introduction to Agentic AI** | *Theory:* agents beyond chat — tools, planning, reasoning; NeMo Retriever & Guardrails. *Lab 8:* build a single agent that retrieves, uses a tool, and returns structured output |
| 12:45 – 13:45 | *Lunch* | |
| 13:45 – 15:15 | **S9 · Text-to-SQL & Multi-Agent Workflows** *(double session)* | *Theory:* NL→SQL translation; multi-agent collaboration; NVIDIA AI Blueprints. *Lab 9A:* build a Text-to-SQL agent over a real database. *Lab 9B:* run a multi-agent workflow and map it to a blueprint |
| 15:15 – 15:30 | *Tea / Coffee* | |
| 15:30 – 17:00 | **S10 · Enterprise RAG, Quality & Governance** | *Theory:* Enterprise RAG reference architecture; evaluation; guardrails and governance. *Lab 10:* guided Enterprise-RAG query flow; analyse grounding. Includes a multimodal (vision) demo with LLaVA |
| 17:00 – 17:15 | **Day 2 Wrap-up & Q&A** | |

**Day 2 outcome:** you can design, implement and teach inference-driven, agentic and blueprint-based AI systems.

---

## Day 3 — HPC, Physical AI, Data Engineering, ML and Capstone

*Day 3 widens the lens — simulation and Physical AI, data engineering, classical ML — and closes with a team capstone.*

| Time | Session | What happens |
|---|---|---|
| 09:15 – 09:30 | *Day 2 recap* | |
| 09:30 – 11:00 | **S11 · AI + HPC, Digital Twins, Physical AI** | *Theory:* AI/HPC convergence; simulation-driven AI; robotics vision. *Lab 11:* compare GenAI vs compute-intensive workloads; simulation environment walkthrough |
| 11:00 – 11:15 | *Tea / Coffee* | |
| 11:15 – 12:45 | **S12 · End-to-End Data Engineering** | *Theory:* projects, workflows, pipelines, connectors. *Lab 12 (7 activities):* load/save data, connectors, workflow I/O, exploration, preparation, join/union, working with code |
| 12:45 – 13:45 | *Lunch* | |
| 13:45 – 15:15 | **S13 · Machine Learning Workflow** | *Lab 13:* feature generation, encoding and scaling; AutoML; model training. Includes a parameter-efficient fine-tuning (QLoRA) demonstration |
| 15:15 – 15:30 | *Tea / Coffee* | |
| 15:30 – 16:45 | **S14 · Capstone Demonstration** | *Lab 14:* in teams, design and demonstrate a complete GenAI solution; explain the architecture; discuss classroom and research adoption |
| 16:45 – 17:15 | **Valedictory, Feedback & Certificates** | |

**Day 3 outcome:** an end-to-end understanding, from GenAI and agents through HPC, simulation and Physical AI to data engineering and ML.

---

## Hands-on lab blocks at a glance

| Lab | Day | Focus | Core technology |
|---|---|---|---|
| 1 | 1 | Platform setup and GPU notebook | Kubeflow, Jupyter |
| 2 | 1 | GPU inspection and baseline workload | GPU tooling |
| 3 | 1 | Open-source LLM comparison and prompting | LLaMA 3.1, Mistral, Phi-3.5 |
| 4A | 1 | Embeddings and vector store | Embedding models, vector DB |
| 4B | 1 | Chunking strategies and retrieval accuracy | Text splitters |
| 5 | 1 | End-to-end RAG application | Retriever + LLM, FAISS |
| 6 | 2 | Notebook → reusable workflow | Workflow automation |
| 7 | 2 | Inference service and concurrency | NVIDIA NIM |
| 8 | 2 | Single-agent workflow with tools | Agents, retrieval |
| 9A | 2 | Text-to-SQL agent | SQL toolkit |
| 9B | 2 | Multi-agent workflow and blueprints | AutoGen |
| 10 | 2 | Enterprise RAG, quality and governance | Blueprints, guardrails |
| 11 | 3 | GenAI vs compute-intensive workloads | HPC, digital twins |
| 12 | 3 | Data engineering (7 activities) | Connectors, pipelines |
| 13 | 3 | ML workflow and AutoML | Feature engineering, QLoRA |
| 14 | 3 | Capstone demonstration | Full stack |

> All labs run inside the private lab environment over VPN. Most labs use the shared
> model-inference service, so you don't need a dedicated GPU for every exercise; the few
> that do (local text generation, image generation, fine-tuning) are scheduled in rotation.
