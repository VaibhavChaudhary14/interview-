import logging
import random

logger = logging.getLogger(__name__)

# Curated fallback question bank per role + topic
FALLBACK_QUESTIONS = {
    "backend_engineer": {
        "API design": [
            "Can you walk me through how you would design a RESTful API for a user authentication system, covering endpoints, status codes, and error handling?",
            "What are the trade-offs between REST and GraphQL, and when would you choose one over the other?",
        ],
        "databases": [
            "Explain how database indexing works and describe a scenario where adding an index could actually hurt performance.",
            "What is the difference between INNER JOIN, LEFT JOIN, and FULL OUTER JOIN? Provide a real-world use case for each.",
        ],
        "caching": [
            "Describe how you would implement a caching layer for a high-traffic API endpoint. What cache invalidation strategy would you use and why?",
            "What is cache stampede, and how can you prevent it in a distributed system?",
        ],
        "concurrency": [
            "Explain the difference between processes and threads. In what scenarios would you use one over the other for a backend service?",
            "How does Python's GIL affect concurrency, and what strategies can you use to achieve true parallelism?",
        ],
        "system design": [
            "Design a URL shortening service like bit.ly. Walk through your architecture decisions, data storage choices, and how you'd handle scale.",
            "How would you design a notification system that needs to deliver millions of push notifications per day reliably?",
        ],
        "testing": [
            "What is the difference between unit tests, integration tests, and end-to-end tests? How would you decide on the right balance for a backend service?",
            "Explain what test-driven development (TDD) means in practice and describe a scenario where it would be particularly valuable.",
        ],
        "security": [
            "How would you prevent SQL injection in a Python application that uses raw SQL queries? What broader security principles apply here?",
            "Explain the OAuth 2.0 flow and describe how you would implement secure API authentication using JWTs.",
        ],
        "performance": [
            "Your API response times have suddenly increased by 3x. Walk me through your debugging process to identify the bottleneck.",
            "What strategies would you use to optimize a database query that is doing a full table scan on a table with 50 million rows?",
        ],
        "general": [
            "Describe a technically challenging backend problem you've solved and explain the approach you took.",
            "What does it mean for a system to be 'highly available'? What architectural patterns support this property?",
        ],
    },
    "ai_ml_engineer": {
        "supervised learning": [
            "Explain the bias-variance trade-off and describe how you would diagnose and address underfitting vs. overfitting in a model.",
            "Compare logistic regression and a gradient boosting classifier for a binary classification task. When would you prefer each?",
        ],
        "neural networks": [
            "Explain how backpropagation works conceptually. What is the chain rule's role in training a neural network?",
            "What is the vanishing gradient problem and what architectural choices can mitigate it?",
        ],
        "NLP": [
            "Explain how transformer attention mechanisms work. What problem do they solve compared to RNNs?",
            "How would you fine-tune a pre-trained language model for a text classification task with limited labeled data?",
        ],
        "model evaluation": [
            "When accuracy is not the right metric, what alternatives would you use and in what scenarios?",
            "Explain k-fold cross-validation. Why is it preferable to a simple train/test split for model selection?",
        ],
        "feature engineering": [
            "Describe three feature engineering techniques you would use for a dataset with high cardinality categorical variables.",
            "How does feature scaling affect gradient descent? Which algorithms require it and which don't?",
        ],
        "deep learning": [
            "Compare CNNs, RNNs, and Transformers — when would you reach for each architecture?",
            "Explain what transfer learning is and why it's particularly valuable when training data is scarce.",
        ],
        "ML ops": [
            "Describe the components of an ML pipeline from data ingestion to model serving. What can go wrong at each stage?",
            "What is model drift? How would you detect it in production and what would you do when you detect it?",
        ],
        "statistics": [
            "Explain the difference between p-value and confidence intervals. Why has p-value significance been criticized in scientific practice?",
            "What is the central limit theorem and why is it foundational for many machine learning statistical assumptions?",
        ],
        "general": [
            "Describe a machine learning project you worked on end-to-end. What was the hardest part and how did you handle it?",
            "What is retrieval-augmented generation (RAG) and what problems does it solve compared to fine-tuning a language model?",
        ],
    },
}


class FallbackProvider:
    """
    Template-based question generator used when OPENAI_API_KEY is not configured.
    Returns deterministic, high-quality questions from a curated bank.
    Implements the same `generate(prompt, **kwargs) -> str` interface as OpenAIProvider.
    """

    def generate(self, prompt: str, **kwargs) -> str:
        # Parse role and topic from the prompt
        role = self._extract_role(prompt)
        topic = self._extract_topic(prompt)

        role_bank = FALLBACK_QUESTIONS.get(role, FALLBACK_QUESTIONS.get("backend_engineer", {}))
        topic_bank = role_bank.get(topic, role_bank.get("general", [
            f"Explain the key concepts related to {topic} in the context of {role}."
        ]))

        question = random.choice(topic_bank)
        logger.info("FallbackProvider: role=%s topic=%s", role, topic)

        # Return in the JSON format the QuestionGeneratorService expects
        import json
        return json.dumps({"topic": topic, "question": question})

    def _extract_role(self, prompt: str) -> str:
        if "ai_ml_engineer" in prompt or "AI/ML" in prompt:
            return "ai_ml_engineer"
        return "backend_engineer"

    def _extract_topic(self, prompt: str) -> str:
        # QuestionGeneratorService embeds the topic in the prompt
        for line in prompt.split("\n"):
            if "Focus:" in line:
                return line.split("Focus:")[-1].strip().rstrip(".")
        return "general"
