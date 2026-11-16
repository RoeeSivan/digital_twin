"""Digital-twin chat with an Actor-Critic review loop.

Agentic AI Systems (Reichman University), assignment 1.
Modules:
    config      - environment, model names, paths, MAX_ATTEMPTS
    context     - loads the background sources (LinkedIn text + personal summary)
    schemas     - Pydantic models: Evaluation, AttemptRecord, QuestionRecord
    llm         - Anthropic client, shared call options, TechnicalError
    actor       - the answer generator (Actor)
    critic      - the answer evaluator (Critic) with structured output, plus a fake critic
    loop        - generate -> evaluate -> fix loop, max 3 attempts
    audit_log   - JSON audit log writer/reader
"""
